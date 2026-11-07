from google import genai

client = genai.Client()

response = client.interactions.create(
    model="gemini-2.5-flash",
    input="Reply with exactly: NetSage AI Gemini connection successful."
)

print(response.output_text)