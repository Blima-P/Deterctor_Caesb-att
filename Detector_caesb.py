import json
import logging
import os
import random
import subprocess
import time
from urllib.parse import urlparse
import threading
import tkinter as tk
from tkinter import scrolledtext

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# ===== CONFIGURAÇÕES =====
BUSCAS = [
    "Caesb",
    "segunda via caesb",
    "caesb pagamento",
    "caesb 2 via conta",
    "conta caesb gov",
]
DOMINIO_CAESB = "caesb.df.gov.br"
ARQUIVO_JSON = "urls_suspeitas_caesb.json"
ARQUIVO_RPA = "denunciar_rpa.ps1"

# ===== LOGGER =====
def configurar_logger():
    os.makedirs("log", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler("log/detector_caesb.log", encoding="utf-8")],
        force=True
    )
    return logging.getLogger("DetectorCaesb")
logger = configurar_logger()

# ===== EXTRAÇÃO DE LINKS PATROCINADOS =====
def extrair_urls_patrocinadas(busca, log_fn):
    perfil_path = os.path.join(os.getcwd(), "perfil_selenium_caesb")
    os.makedirs(perfil_path, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={perfil_path}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    urls_patrocinadas = []

    try:
        log_fn(f"🔍 Buscando: {busca}")
        driver.get("https://www.google.com")
        time.sleep(random.uniform(2, 3))

        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(busca)
        search_box.send_keys(Keys.RETURN)
        time.sleep(random.uniform(5, 7))

        def eh_suspeita(href):
            if not href:
                return False
            dominio = urlparse(href).netloc
            return DOMINIO_CAESB not in dominio

        # (1) Anúncios com link direto
        ads_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'googleadservices.com')]")
        for link in ads_links:
            href = link.get_attribute("href")
            if eh_suspeita(href):
                dominio = urlparse(href).netloc
                urls_patrocinadas.append({"url": href, "dominio": dominio})
                log_fn(f"🔗 (1) Patrocinado SUSPEITO: {dominio} → {href}")

        # (2) Blocos com texto "Anúncio" ou "Patrocinado"
        blocos_anuncio = driver.find_elements(By.XPATH, "//span[.='Anúncio' or .='Patrocinado']/ancestor::div[contains(@data-hveid, '')]")
        for bloco in blocos_anuncio:
            try:
                link = bloco.find_element(By.XPATH, ".//a[@href]")
                href = link.get_attribute("href")
                if eh_suspeita(href):
                    dominio = urlparse(href).netloc
                    urls_patrocinadas.append({"url": href, "dominio": dominio})
                    log_fn(f"🔗 (2) Patrocinado SUSPEITO: {dominio} → {href}")
            except:
                continue

        # (3) DIVs com marcação de anúncio
        divs_patrocinadas = driver.find_elements(By.XPATH, "//div[@data-text-ad or @aria-label='Ads']")
        for div in divs_patrocinadas:
            try:
                a = div.find_element(By.XPATH, ".//a[@href]")
                href = a.get_attribute("href")
                if eh_suspeita(href):
                    dominio = urlparse(href).netloc
                    urls_patrocinadas.append({"url": href, "dominio": dominio})
                    log_fn(f"🔗 (3) Patrocinado SUSPEITO: {dominio} → {href}")
            except:
                continue

    except Exception as e:
        log_fn(f"❌ Erro na extração: {e}")
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

# ===== RPA =====
def executar_rpa(log_fn):
    try:
        subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ARQUIVO_RPA], check=True)
        log_fn("🤖 RPA executada com sucesso.")
    except subprocess.CalledProcessError as e:
        log_fn(f"❌ Falha na execução da RPA: {e}")

# ===== GUI =====
def iniciar_gui():
    janela = tk.Tk()
    janela.title("Detector de Anúncios – CAESB")
    janela.geometry("700x500")

    texto = scrolledtext.ScrolledText(janela, wrap=tk.WORD, width=80, height=25)
    texto.pack(padx=10, pady=10)

    def log_gui(msg):
        texto.insert(tk.END, msg + "\n")
        texto.see(tk.END)
        logger.info(msg)

    def processar():
        texto.delete("1.0", tk.END)
        log_gui("🚰 Iniciando varredura para CAESB...\n")
        urls_suspeitas = []

        for termo in BUSCAS:
            urls_suspeitas.extend(extrair_urls_patrocinadas(termo, log_gui))

        salvar_json(urls_suspeitas)

        if urls_suspeitas:
            log_gui("\n🔴 Links patrocinados SUSPEITOS detectados:")
            for u in urls_suspeitas:
                log_gui(f" → {u['dominio']} | {u['url']}")
            log_gui("\n🤖 Executando RPA...\n")
            executar_rpa(log_gui)
        else:
            log_gui("\n✅ Nenhum link suspeito foi detectado.")

    botao = tk.Button(janela, text="Iniciar varredura", command=lambda: threading.Thread(target=processar).start())
    botao.pack(pady=5)

    janela.mainloop()

# ===== EXECUÇÃO =====
if __name__ == "__main__":
    iniciar_gui()
