import os
import io
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from openai import OpenAI

# Initialize API Keys from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure Clients
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")
openai_client = OpenAI(api_key=OPENAI_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("System initialized. Dual-brain AI redundancy online.")


def process_text_gemini(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return response.text


def process_text_openai(prompt: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def process_image_gemini(image_bytes: bytes, caption: str) -> str:
    from PIL import Image
    image = Image.open(io.BytesIO(image_bytes))
    prompt = caption if caption else "Analyze this image."
    response = gemini_model.generate_content([prompt, image])
    return response.text


def process_image_openai(image_bytes: bytes, caption: str) -> str:
    import base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt = caption if caption else "Analyze this image."
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
    )
    return response.choices[0].message.content


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    try:
        # Primary: Gemini
        reply = await asyncio.to_thread(process_text_gemini, user_text)
    except Exception as e:
        # Fallback: OpenAI
        try:
            reply = await asyncio.to_thread(process_text_openai, user_text)
        except Exception as fallback_e:
            reply = f"System Error: Both Gemini and OpenAI pipelines failed.\nGemini: {e}\nOpenAI: {fallback_e}"

    await update.message.reply_text(reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    caption = update.message.caption or ""

    try:
        # Primary: Gemini
        reply = await asyncio.to_thread(process_image_gemini, bytes(image_bytes), caption)
    except Exception as e:
        # Fallback: OpenAI
        try:
            reply = await asyncio.to_thread(process_image_openai, bytes(image_bytes), caption)
        except Exception as fallback_e:
            reply = f"System Error: Both Gemini and OpenAI vision pipelines failed.\nGemini: {e}\nOpenAI: {fallback_e}"

    await update.message.reply_text(reply)


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()


if __name__ == "__main__":
    main()
  
