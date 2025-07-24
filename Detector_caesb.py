import json
import logging
import os
import random
import subprocess
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# ===== CONFIGURAÇÕES =====
BUSCAS = [
    "caesb segunda via",
    "portal caesb",
    "conta caesb",
    "caesb consultar falta de água"
]
ARQUIVO_JSON = "urls_suspeitas.json"
ARQUIVO_RPA = "denunciar_rpa.ps1"

# ===== LOGGER =====
def configurar_logger():
    os.makedirs("log", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("log/detector.log", encoding="utf-8")
        ],
        force=True
    )
    return logging.getLogger("Detector")
logger = configurar_logger()

# ===== EXTRAÇÃO DE LINKS PATROCINADOS =====
def extrair_urls_patrocinadas(busca):
    perfil_path = os.path.join(os.getcwd(), "perfil_selenium")
    os.makedirs(perfil_path, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={perfil_path}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    urls_patrocinadas = []
    try:
        logger.info(f"🔍 Buscando: {busca}")
        driver.get("https://www.google.com")
        time.sleep(random.uniform(2, 4))

        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(busca)
        search_box.send_keys(Keys.RETURN)

        time.sleep(random.uniform(5, 7))
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Busca por divs que geralmente representam anúncios patrocinados
        ad_divs = soup.find_all('div', attrs={"data-text-ad": True})
        for ad in ad_divs:
            a_tag = ad.find('a', href=True)
            if a_tag and "/url?q=" in a_tag['href']:
                url = a_tag['href'].split("/url?q=")[1].split("&")[0]
                dominio = urlparse(url).netloc
                urls_patrocinadas.append({
                    "url": url,
                    "dominio": dominio
                })
                logger.warning(f"⚠️ Link patrocinado detectado: {dominio} → {url}")

        # Busca por spans com texto "Anúncio" ou "Patrocinado" (fallback)
        spans = soup.find_all('span', string=lambda s: s and ('Patrocinado' in s or 'Anúncio' in s))
        for tag in spans:
            parent = tag.find_parent('div')
            if parent:
                a_tag = parent.find('a', href=True)
                if a_tag and "/url?q=" in a_tag['href']:
                    url = a_tag['href'].split("/url?q=")[1].split("&")[0]
                    dominio = urlparse(url).netloc
                    urls_patrocinadas.append({
                        "url": url,
                        "dominio": dominio
                    })
                    logger.warning(f"⚠️ Link patrocinado detectado: {dominio} → {url}")

        # Busca por divs com classes comuns de anúncios (exemplo: 'uEierd', 'V0MxL')
        ad_classes = ['uEierd', 'V0MxL']
        for cls in ad_classes:
            for ad in soup.find_all('div', class_=cls):
                a_tag = ad.find('a', href=True)
                if a_tag and "/url?q=" in a_tag['href']:
                    url = a_tag['href'].split("/url?q=")[1].split("&")[0]
                    dominio = urlparse(url).netloc
                    urls_patrocinadas.append({
                        "url": url,
                        "dominio": dominio
                    })
                    logger.warning(f"⚠️ Link patrocinado detectado: {dominio} → {url}")
    except Exception as e:
        logger.error(f"❌ Erro durante a extração: {e}")
    finally:
        driver.quit()

    return urls_patrocinadas

# ===== SALVAR JSON =====
def salvar_json(urls):
    dados = {
        "suspeitas_detectadas_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "urls_suspeitas": urls,
        "status": "anomalia_detectada" if urls else "nenhuma_anomalia"
    }
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    logger.info(f"💾 JSON salvo: {ARQUIVO_JSON}")

# ===== RPA =====
def executar_rpa():
    try:
        subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ARQUIVO_RPA], check=True)
        logger.info("🤖 RPA executada com sucesso.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Falha na execução da RPA: {e}")

# ===== MAIN =====
def main():
    print("\n🚨 Iniciando verificação de links patrocinados...\n")
    urls_suspeitas = []

    for termo in BUSCAS:
        urls_suspeitas.extend(extrair_urls_patrocinadas(termo))

    salvar_json(urls_suspeitas)

    if urls_suspeitas:
        print("\n🔴 Links patrocinados detectados:")
        for u in urls_suspeitas:
            print(f" → {u['dominio']} | {u['url']}")
        print("\n🤖 Executando RPA...\n")
        executar_rpa()
    else:
        print("\n✅ Nenhum link patrocinado foi detectado.\n")

if __name__ == "__main__":
    main()
