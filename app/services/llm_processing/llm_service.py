import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from app.api.schemas.schemas import GeneratedParser
from app.services.llm_processing.prompts import CODE_GEN_PROMPT

load_dotenv()


class CodeGeneratorService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
        self.structured_llm = self.llm.with_structured_output(GeneratedParser)

    async def generate_parser_code_async(self, json_snippet: str) -> GeneratedParser:
        prompt = ChatPromptTemplate.from_template(CODE_GEN_PROMPT)
        chain = prompt | self.structured_llm
        try:
            return await chain.ainvoke({"context_data": json_snippet})
        except Exception as e:
            print(f"❌ Ошибка асинхронной генерации кода: {e}")
            return GeneratedParser(explanation="Error", python_code="")
