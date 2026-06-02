import google.generativeai as genai

# Cole a sua chave AQ... aqui dentro das aspas apenas para este teste rápido
CHAVE = "COLE_SUA_CHAVE_AQUI" 
genai.configure(api_key=CHAVE)

print("A conectar aos servidores da Google...")
print("Modelos disponíveis que suportam geração de conteúdo (Visão/Texto):\n")

try:
    # Interroga a API sobre todos os modelos atrelados à sua chave
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Nome exato a ser usado no código: '{m.name}'")
    print("\nDiagnóstico concluído.")
except Exception as e:
    print(f"Ocorreu um erro no diagnóstico: {e}")