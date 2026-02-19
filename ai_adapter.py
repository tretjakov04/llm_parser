from openai import OpenAI

class AIAdapter:
    def __init__(self, api_key):
        """
        Инициализация. Принимаем ключ, который нам передали из main.py
        """
        self.client = OpenAI(api_key=api_key)

    def get_simple_response(self, prompt, model="gpt-4o"):
        """
        Метод отправляет текст (prompt) в GPT и возвращает текстовый ответ.
        """
        try:
            print(f"Запрос к модели {model}...")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Ты полезный помощник."},
                    {"role": "user", "content": prompt}
                ]
            )
            # Возвращаем только текст ответа
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Ошибка при запросе к API: {e}"