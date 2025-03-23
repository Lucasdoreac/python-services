# python-services

Guia de como baixar os serviços necessários para a execução do projeto Back-And.

## Ferramentas - Configurando ambiente

[![Pycharm](https://img.shields.io/badge/PYCHARM-000000)](https://www.jetbrains.com/help/pycharm/getting-started.html)
[![Poetry](https://img.shields.io/badge/POETRY-000000)](https://python-poetry.org/docs/)
[![Dotenv](https://img.shields.io/badge/DOTENV-000000)](https://www.dotenv.org/docs/)

## Poetry
O Poetry é uma ferramenta para gerenciamento de dependências e empacotamento em Python. Ele facilita a instalação de bibliotecas, criação de ambientes virtuais e publicação de projetos.

[Install Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)

## PyCharm
PyCharm é um ambiente de desenvolvimento integrado (IDE) para Python, desenvolvido pela JetBrains.

!Importante: Não instale em "C:\Program Files\JetBrains\PyCharm 2024", use um diretório sem espaços. Isso é importante para evitar problemas com o Poetry e com a depuração.

[Install Pycharm](https://www.jetbrains.com/pycharm/download/)

## Criando ambiente virtual

1. poetry env use python3.12

### Se quiser ativar o ambiente virtual

```bash
poetry shell
```

## Instalar e configurar o Poetry no PyCharm
https://www.jetbrains.com/help/pycharm/poetry.html#poetry-env


## Instalar dependências com Poetry
```bash
poetry install
```
