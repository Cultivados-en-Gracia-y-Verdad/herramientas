from ollama import Client

# Initialize the client
client = Client(model="codex")

def generate_code(prompt):
    response = client.generate(prompt=prompt)
    return response.choices[0].text

if __name__ == "__main__":
    prompt = "Write a Python function to sort a list of numbers."
    generated_code = generate_code(prompt)
    print(generated_code.strip())
