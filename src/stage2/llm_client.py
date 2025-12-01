import os
from openai import OpenAI
from anthropic import Anthropic

class LLMClient:
    def __init__(self, provider="openai", model="gpt-4o-mini"):
        self.provider = provider

        if provider == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = model

        elif provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = model

    def run(self, system_prompt, user_prompt):
        if self.provider == "openai":
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return completion.choices[0].message.content

        if self.provider == "anthropic":
            completion = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return completion.content[0].text
