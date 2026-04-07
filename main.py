import getpass
import sys

from src.auth import login
from src.api_client import create_session
from src.config import fetch_config, get_catalogs
from src.filters import fetch_all_filter_options
from src.questions import fetch_all_questions
from src.html_generator import generate_html


def main():
    print("=" * 50)
    print("  Estrategia Med - Download de Questoes")
    print("=" * 50)

    email = input("\nEmail: ").strip()
    password = getpass.getpass("Senha: ")

    if not email or not password:
        print("Email e senha sao obrigatorios.")
        sys.exit(1)

    # 1. Login
    print("\n[1/5] Fazendo login...")
    try:
        token = login(email, password)
        print("Login realizado com sucesso!")
    except Exception as e:
        print(f"Erro no login: {e}")
        sys.exit(1)

    # 2. Criar sessao
    session = create_session(token)

    # 3. Buscar config
    print("\n[2/5] Buscando configuracao de filtros...")
    try:
        config = fetch_config(session)
        catalogs = get_catalogs(config)
        print(f"Encontrados {len(catalogs)} tipos de filtro.")
    except Exception as e:
        print(f"Erro ao buscar config: {e}")
        sys.exit(1)

    # 4. Buscar opcoes de filtros
    print("\n[3/5] Buscando opcoes de filtros...")
    try:
        filter_options = fetch_all_filter_options(session, catalogs)
    except Exception as e:
        print(f"Erro ao buscar filtros: {e}")
        filter_options = {}

    # 5. Buscar questoes
    print("\n[4/5] Buscando questoes...")
    try:
        questions = fetch_all_questions(session, config, catalogs)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario. Cache salvo.")
        sys.exit(0)
    except Exception as e:
        print(f"Erro ao buscar questoes: {e}")
        print("Tentando gerar HTML com questoes do cache...")
        from src.questions import load_cache
        questions = load_cache()
        if not questions:
            print("Nenhuma questao disponivel.")
            sys.exit(1)

    # 6. Gerar HTML
    print("\n[5/5] Gerando HTML...")
    generate_html(questions, filter_options, "questoes.html")

    print("\nConcluido! Abra o arquivo 'questoes.html' no navegador.")


if __name__ == "__main__":
    main()
