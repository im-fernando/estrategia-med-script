import getpass
import os
import sys

from src.auth import login, load_token_from_cookies, has_cookies_file
from src.api_client import create_session
from src.config import fetch_config, get_catalogs
from src.filters import fetch_all_filter_options
from src.questions import fetch_all_questions, fetch_test_questions
from src.html_generator import generate_html


def main():
    print("=" * 50)
    print("  Estrategia Med - Download de Questoes")
    print("=" * 50)

    # 1. Autenticacao
    print("\nAutenticacao:")
    if has_cookies_file():
        print("  [1] Usar cookies.txt (detectado!)")
        print("  [2] Login com email/senha")
        auth_choice = input("\nEscolha (1 ou 2) [1]: ").strip() or "1"
    else:
        print("  [1] Login com email/senha")
        print("  [2] Usar cookies.txt (coloque o arquivo na raiz do projeto)")
        auth_choice = input("\nEscolha (1 ou 2) [1]: ").strip() or "1"

    token = None
    if (has_cookies_file() and auth_choice == "1") or (not has_cookies_file() and auth_choice == "2"):
        # Usar cookies.txt
        print("\n[1/5] Carregando token do cookies.txt...")
        try:
            token = load_token_from_cookies()
            print("Token carregado com sucesso!")
        except Exception as e:
            print(f"Erro ao carregar cookies: {e}")
            sys.exit(1)
    else:
        # Login com email/senha
        email = input("\nEmail: ").strip()
        password = getpass.getpass("Senha: ")
        if not email or not password:
            print("Email e senha sao obrigatorios.")
            sys.exit(1)

        print("\n[1/5] Fazendo login...")
        try:
            token = login(email, password)
            print("Login realizado com sucesso!")
        except Exception as e:
            print(f"Erro no login: {e}")
            if "CAPTCHA" in str(e) or "captcha" in str(e):
                print("\n  DICA: A API exige CAPTCHA. Use cookies.txt do navegador:")
                print("  1. Instale a extensao 'Cookie-Editor' no Chrome")
                print("  2. Faca login no site med.estrategia.com")
                print("  3. Exporte os cookies (formato Netscape/txt)")
                print("  4. Salve como 'cookies.txt' na raiz do projeto")
            sys.exit(1)

    # Modo de download
    print("\nModo de download:")
    print("  [1] Completo - todas as questoes (pode demorar bastante)")
    print("  [2] Teste - 15 questoes por topico/subtopico (rapido, pra validar)")
    mode = input("\nEscolha (1 ou 2): ").strip()
    test_mode = mode == "2"

    if test_mode:
        print("\n*** MODO TESTE - 15 questoes por topico ***\n")

    # 2. Criar sessao
    session = create_session(token)

    # 3. Buscar config
    print("[2/5] Buscando configuracao de filtros...")
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
        if test_mode:
            questions = fetch_test_questions(
                session, config, catalogs, filter_options, per_topic=15
            )
        else:
            fetch_all_questions(session, config, catalogs, filter_options)
            questions = None  # Sera lido do disco no gerador
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario. Cache salvo.")
        questions = None
    except Exception as e:
        print(f"Erro ao buscar questoes: {e}")
        print("Tentando gerar HTML com questoes do cache...")
        questions = None

    # 6. Gerar HTML
    output = "questoes_teste.html" if test_mode else "questoes.html"
    print(f"\n[5/5] Gerando HTML ({output})...")
    if questions is not None:
        # Modo teste: questoes ja na memoria
        generate_html(questions, filter_options, output)
    else:
        # Modo completo: ler do JSONL em streaming
        from src.questions import CACHE_FILE, load_cache
        if not os.path.exists(CACHE_FILE):
            print("Nenhuma questao disponivel.")
            sys.exit(1)
        print(f"Carregando questoes do cache ({CACHE_FILE})...")
        questions = load_cache()
        if not questions:
            print("Nenhuma questao disponivel.")
            sys.exit(1)
        print(f"  {len(questions)} questoes carregadas.")
        generate_html(questions, filter_options, output)

    print(f"\nConcluido! Abra o arquivo '{output}' no navegador.")


if __name__ == "__main__":
    main()
