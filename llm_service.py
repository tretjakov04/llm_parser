import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from schemas import GeneratedParser
from prompts import CODE_GEN_PROMPT

load_dotenv()


class CodeGeneratorService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,  # Код требует точности
            api_key=api_key
        )
        # Мы ждем от GPT объект с кодом
        self.structured_llm = self.llm.with_structured_output(GeneratedParser)

    def generate_parser_code(self, json_snippet: str) -> GeneratedParser:
        """Отправляет сэмпл файла и получает готовый Python-код"""
        prompt = ChatPromptTemplate.from_template(CODE_GEN_PROMPT)
        chain = prompt | self.structured_llm

        try:
            return chain.invoke({"context_data": json_snippet})
        except Exception as e:
            print(f"❌ Ошибка генерации кода: {e}")
            return GeneratedParser(explanation="Error", python_code="")