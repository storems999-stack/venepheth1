interface Env {
	BACKEND_URL?: string;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const backendOrigin = env.BACKEND_URL || "https://led-highlighted-concentration-five.trycloudflare.com";
		const clientUrl = new URL(request.url);
		const targetUrl = new URL(clientUrl.pathname + clientUrl.search, backendOrigin);

		const reqHeaders = new Headers(request.headers);
		reqHeaders.set("Host", new URL(backendOrigin).host);
		reqHeaders.set("X-Forwarded-Host", clientUrl.host);
		reqHeaders.set("X-Forwarded-Proto", clientUrl.protocol.replace(":", ""));

		const proxyRequest = new Request(targetUrl.toString(), {
			method: request.method,
			headers: reqHeaders,
			body: request.body,
			redirect: "manual",
		});

		try {
			const response = await fetch(proxyRequest);

			// Adjust redirect Location header so client stays on worker domain
			const responseHeaders = new Headers(response.headers);
			const location = responseHeaders.get("Location");
			if (location) {
				const backendHost = new URL(backendOrigin).host;
				responseHeaders.set("Location", location.replace(backendHost, clientUrl.host));
			}

			return new Response(response.body, {
				status: response.status,
				statusText: response.statusText,
				headers: responseHeaders,
			});
		} catch (err: any) {
			return new Response(`Error connecting to Django backend: ${err?.message || err}`, {
				status: 502,
				headers: { "Content-Type": "text/plain;charset=UTF-8" },
			});
		}
	},

	async queue(batch: any, env: Env): Promise<void> {
		for (let message of batch.messages) {
			console.log(`Queue message:`, message.body);
		}
	},
};
