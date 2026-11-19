import unittest
from unittest.mock import patch

from src.api import ChatRequest, chat


class ChatApiTests(unittest.TestCase):
    @patch("src.api.generate_supervisor_reply")
    def test_chat_endpoint_returns_the_supervisor_reply(self, generate_supervisor_reply):
        generate_supervisor_reply.return_value = "Here are the requested records."
        request = ChatRequest(
            messages=[
                {"role": "user", "text": "Show today's attendance."},
            ]
        )

        response = chat(request)

        self.assertEqual(response, {"reply": "Here are the requested records."})
        generate_supervisor_reply.assert_called_once_with(
            [("user", "Show today's attendance.")]
        )


if __name__ == "__main__":
    unittest.main()
