from dotenv import load_dotenv

_ = load_dotenv()

from branchout.agent.agent import Agent

WELCOME = """
🌱 Branchout — seu guia de carreira em tecnologia

Não sabe qual área seguir? Eu te ajudo a descobrir e monto um roadmap
de estudos gratuito, do zero. Para começar, me conte um pouco sobre você.

(digite "sair" para encerrar)
"""

EXIT_WORDS = {"sair", "exit", "quit"}


def main():
    agent = Agent()
    print(WELCOME)
    while True:
        try:
            message = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.lower() in EXIT_WORDS:
            break
        if message:
            print(f"\nBranchout: {agent.request(message, '1')}\n")
    print("\nAté a próxima! 🚀")
