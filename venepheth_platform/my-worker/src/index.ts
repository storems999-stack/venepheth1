interface Env {
	DJANGO_BACKEND_ORIGIN: string;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const backendUrl = env.DJANGO_BACKEND_ORIGIN?.trim();
		if (!backendUrl) {
			return new Response("Worker misconfigured: DJANGO_BACKEND_ORIGIN is required", {
				status: 503,
				headers: { "Content-Type": "text/plain;charset=UTF-8" },
			});
		}

		let backendOrigin: URL;
		try {
			backendOrigin = new URL(backendUrl);
		} catch {
			return new Response("Worker misconfigured: DJANGO_BACKEND_ORIGIN must be a valid origin", {
				status: 503,
				headers: { "Content-Type": "text/plain;charset=UTF-8" },
			});
		}

		const isLoopback = ["localhost", "127.0.0.1", "[::1]"].includes(backendOrigin.hostname);
		if (
			(backendOrigin.protocol !== "https:" && !(isLoopback && backendOrigin.protocol === "http:")) ||
			backendOrigin.username ||
			backendOrigin.password ||
			backendOrigin.pathname !== "/" ||
			backendOrigin.search ||
			backendOrigin.hash
		) {
			return new Response("Worker misconfigured: DJANGO_BACKEND_ORIGIN must be an HTTPS origin", {
				status: 503,
				headers: { "Content-Type": "text/plain;charset=UTF-8" },
			});
		}

		const clientUrl = new URL(request.url);
		const targetUrl = new URL(clientUrl.pathname + clientUrl.search, backendOrigin);

		const reqHeaders = new Headers(request.headers);
		reqHeaders.set("Host", backendOrigin.host);
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
				try {
					const redirectUrl = new URL(location, backendOrigin);
					if (redirectUrl.origin === backendOrigin.origin) {
						redirectUrl.host = clientUrl.host;
						responseHeaders.set("Location", redirectUrl.toString());
					}
				} catch {
					// Preserve non-URL Location values unchanged.
				}
			}

			return new Response(response.body, {
				status: response.status,
				statusText: response.statusText,
				headers: responseHeaders,
			});
		} catch (err: unknown) {
			console.error("Failed to connect to the configured Django backend", err);
			return new Response("Error connecting to Django backend", {
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
