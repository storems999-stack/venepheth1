"""
Grounded Academic Fallback Adapter.
Provides zero-cost, privacy-first, local academic synthesis directly from
retrieved database records without requiring an external paid LLM.
Conforms to Section 2 & 50 of vision.txt (Zero-Cost Enterprise & AI Adapter).
"""

from typing import Any

from .base import BaseLLMAdapter


class GroundedFallbackAdapter(BaseLLMAdapter):
    """Synthesizes academic answers directly from grounded platform data."""

    def generate_response(
        self,
        query: str,
        context_items: list[dict[str, Any]],
        language: str = "en",
    ) -> dict[str, Any]:
        is_lao = language == "lo"

        if not context_items:
            if is_lao:
                answer = (
                    f'ຂໍອະໄພ, ບໍ່ພົບຂໍ້ມູນທີ່ກ່ຽວຂ້ອງໂດຍກົງກັບ: "**{query}**" ໃນຖານຂໍ້ມູນວິຊາການ.\n\n'
                    "💡 **ຄຳແນະນຳທີ່ທ່ານສາມາດຖາມໄດ້:**\n"
                    "- *ເວລາຮັບນັກສຶກສາ (Office Hours) ຂອງອາຈານແມ່ນຕອນໃດ?*\n"
                    "- *ອາຈານສອນວິຊາຫຍັງແດ່? (Courses)*\n"
                    "- *ມີສິ່ງຕີພິມ ຫຼື ບົດຄົ້ນຄ້ວາໃດແດ່? (Publications)*"
                )
            else:
                answer = (
                    f'I couldn\'t find any direct academic records matching: "**{query}**".\n\n'
                    "💡 **Here are some suggested topics you can explore:**\n"
                    "- *When are the professor's office hours?*\n"
                    "- *What courses are currently offered?*\n"
                    "- *Recent publications on Business Management or Economics*"
                )
            return {
                "answer": answer,
                "sources": [],
                "provider": "Local Academic Knowledge Engine",
            }

        # Format retrieved items into an answer
        lines = []
        if is_lao:
            lines.append(f'ອີງຕາມຖານຂໍ້ມູນວິຊາການຂອງ ອາຈານ ວີນພເຈດ ສາຍາວົງ ສຳລັບຫົວຂໍ້ "**{query}**":\n')
        else:
            lines.append(f'Based on the academic records of Lecturer Venepheth SAYAVONG regarding "**{query}**":\n')

        sources = []
        for idx, item in enumerate(context_items[:5], 1):
            category = item.get("type", "General")
            title = item.get("title", "Untitled")
            summary = item.get("summary", "")
            url = item.get("url", "#")
            extra = item.get("extra", "")

            sources.append(
                {
                    "title": title,
                    "type": category,
                    "url": url,
                }
            )

            lines.append(f"### {idx}. [{category}] [{title}]({url})")
            if summary:
                lines.append(f"{summary}")
            if extra:
                lines.append(f"*{extra}*")
            lines.append("")

        if is_lao:
            lines.append("📌 *ທ່ານສາມາດກົດທີ່ລິ້ງດ້ານເທິງເພື່ອເບິ່ງລາຍລະອຽດ ຫຼື ດາວໂຫຼດເອກະສານ.*")
        else:
            lines.append(
                "📌 *Click any of the links above to inspect the complete syllabus, abstract, or download resources.*"
            )

        return {
            "answer": "\n".join(lines),
            "sources": sources,
            "provider": "Local Academic Knowledge Engine",
        }
