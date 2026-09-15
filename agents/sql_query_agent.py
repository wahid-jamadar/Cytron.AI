import logging
from typing import Dict, Any

from config.settings import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

class SQLQueryAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.1
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert SQL Query Generator. Convert the given natural language requirements into optimized SQL queries. Provide the SQL query and a brief explanation of how it works. Ensure the query follows best practices."),
            ("user", "{requirements}")
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def generate_query(self, requirements: str) -> Dict[str, Any]:
        logger.info("Generating SQL query from requirements...")
        try:
            result = await self.chain.ainvoke({"requirements": requirements})
            return {
                "status": "success",
                "output": result
            }
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
