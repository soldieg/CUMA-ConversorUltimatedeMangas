<p align="center">
  <img src="assets/cuma_logo.png" alt="Logo CUMA" width="580">
</p>
# CUMA

**CUMA - Conversor Ultimate de Mangás**

Aplicativo desktop para Windows voltado para limpeza e conversão de PDFs, imagens, EPUB e XTCH, com foco em leitura de mangás, quadrinhos e arquivos escaneados.
Criado para facilitar a crição de mangas apartir de imagens e pdf para Ereaders, como: Xteink X4 e X3, Kindles, kobo, e um perfil personalizado para a sua resolução, Retirando partes não necessarias deixando apenas a imagem em si. Por exemplo um manga ou quadrinho retirado em pdf de um site de leitura online.

Caso queria ajudar no projeto serei muito grato. 

Não sou programador, mas entendo um pouco da logica de programação. Criei este programa usando o Copilot e o ChatGPT para resolver um problema de ler, criar e converter alguns mangas não disponiveis de forma facil e um unico lugar.


## Apoie o projeto

<p align="center">
  <a href="https://nubank.com.br/cobrar/1i9x4q/6a39f5ae-b88c-4be2-9040-0a7d703e2a02">
    Clique aqui para apoiar via Pix
  </a>
</p>

<p align="center">
  <a href="https://www.buymeacoffee.com/soldieg" target="_blank">
      <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" >
  </a>
</p>

## Recursos principais

- Limpeza de páginas vazias ou pouco úteis em PDFs.
- Exportação em PDF, CBZ, PDF + CBZ e imagens.
- Conversão PDF → EPUB baseado em imagens.
- Conversão PDF → XTCH.
- Conversão EPUB → XTCH.
- Criação de PDF a partir de imagens.
- Temas visuais, incluindo temas CUMA baseados no ícone.
- Configurações preservadas em `%APPDATA%\CUMA\cuma_settings.json`.
- Sistema de atualização por manifesto JSON no GitHub.

## Download

A versão mais recente: <a href="https://github.com/soldiego/CUMA/releases">BAIXAR</a>

## Instalação

1. Baixe `CUMA_windows.zip` em Releases.
2. Extraia o ZIP inteiro.
3. Abra `cuma.exe`.
4. Não apague a pasta `_internal`.

## Configurações do usuário

As configurações, logs e estado do usuário ficam fora da pasta do programa:

```text
%APPDATA%\CUMA\
  cuma_settings.json
  CUMA.log
  erro.txt
```

Isso permite atualizar o programa sem perder preferências.

## Desenvolvimento

Para rodar pelo Python:

```bash
pip install -r requirements.txt
python cuma.py
```

Para compilar no Windows:

```bat
criar_exe_windows_e_zip.bat
```

## Fontes, referências e componentes utilizados

Esta seção lista as fontes de código, bibliotecas, repositórios, serviços e especificações técnicas identificados no projeto. Não se trata de fontes tipográficas.

### Código-fonte e distribuição do CUMA

- **Repositório do CUMA:** `https://github.com/soldiego/CUMA`
- **GitHub Releases do CUMA:** `https://github.com/soldiego/CUMA/releases`
- **Manifesto de atualização estável:** `https://raw.githubusercontent.com/soldiego/CUMA/main/updates/stable.json`
- **Arquivo de atualização distribuído:** `https://github.com/soldiego/CUMA/releases/download/v1.081.2/CUMA_windows.zip`

### Referência XTCH/XTH/XTEINK

- **xtcjs / referência relacionada ao formato XTC/XTCH:** `https://github.com/varo6/xtcjs`

O código do CUMA mantém uma referência explícita a esse repositório em `XTCJS_REPO_URL`. As rotinas atuais do CUMA geram XTCH/XTH nativamente em Python, sem executar Node, npm, Bun ou workers externos, mas essa referência deve ser mantida nos créditos por estar relacionada à implementação/entendimento do formato.

### Bibliotecas Python usadas pelo aplicativo

- **Python / CPython:** `https://github.com/python/cpython`
- **PyMuPDF:** `https://github.com/pymupdf/PyMuPDF`
- **MuPDF, motor base usado pelo PyMuPDF:** `https://github.com/ArtifexSoftware/mupdf`
- **Pillow / PIL:** `https://github.com/python-pillow/Pillow`
- **NumPy:** `https://github.com/numpy/numpy`
- **tkinterdnd2, drag-and-drop opcional:** `https://github.com/pmgagne/tkinterdnd2`
- **PyInstaller, empacotamento do executável Windows:** `https://github.com/pyinstaller/pyinstaller`
- **OpenCV, usado apenas se disponível para detecção CUDA/OpenCL:** `https://github.com/opencv/opencv`

### Bibliotecas padrão do Python usadas no código

O CUMA também usa módulos da biblioteca padrão do Python, incluindo:

- `html`
- `json`
- `os`
- `queue`
- `re`
- `shutil`
- `subprocess`
- `sys`
- `threading`
- `traceback`
- `time`
- `collections`
- `concurrent.futures`
- `uuid`
- `hashlib`
- `struct`
- `zipfile`
- `colorsys`
- `dataclasses`
- `datetime`
- `io`
- `pathlib`
- `typing`
- `ctypes`
- `winreg`
- `urllib.request`
- `locale`
- `webbrowser`

### Interface gráfica

- **Tkinter:** biblioteca gráfica incluída com Python em builds comuns do Windows.
- **Tcl/Tk:** `https://www.tcl.tk/`
- **Tk/Ttk:** usado para widgets, abas, botões, comboboxes, treeviews, barras de rolagem e temas.

### Especificações e formatos usados

- **PDF:** manipulado via PyMuPDF/MuPDF.
- **EPUB:** pacote ZIP com estrutura OPF/XHTML/imagens.
- **CBZ:** arquivo ZIP contendo imagens, usado por leitores de quadrinhos.
- **ZIP:** usado por EPUB, CBZ e pacotes de atualização.
- **XHTML:** `http://www.w3.org/1999/xhtml`
- **OPF / IDPF:** `http://www.idpf.org/2007/opf`
- **OPS / IDPF:** `http://www.idpf.org/2007/ops`
- **Dublin Core Metadata:** `http://purl.org/dc/elements/1.1/`
- **JPEG/JPG, PNG, WebP, BMP, TIFF:** formatos de imagem lidos/escritos via Pillow.
- **SHA-256:** usado para validar integridade do ZIP de atualização.
- **MD5:** usado internamente em páginas XTH/XTCH para digest curto de dados de página.
