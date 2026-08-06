# Dashboard-de-Vendas-NoSQL

# Instruções de uso da aplicação local

## O que é esta aplicação
Esta aplicação é um dashboard interativo de vendas desenvolvido em Streamlit e conectado ao MongoDB. Ela mostra métricas, gráficos, filtros e um relatório executivo com base nos dados da coleção `base.vendas`.

## Requisitos
- Python instalado no computador
- MongoDB em execução localmente
- Os pacotes do projeto instalados no ambiente atual

## Como executar
1. Abra um terminal na pasta do projeto.
2. Garanta que o MongoDB esteja rodando na máquina local.
3. Execute o comando abaixo:

```bash
python -m streamlit run projeto_final.py
```

4. O navegador vai abrir automaticamente. Se isso não acontecer, acesse o endereço exibido no terminal, normalmente:

```text
http://localhost:8501
```

## Como usar o dashboard
- Use os filtros da barra lateral para refinar os dados por categoria, produto, cidade, canal de venda, forma de pagamento, cliente e período.
- A aba **Resumo** mostra os principais indicadores e os gráficos principais.
- A aba **Produtos** traz ranking e análise por produto.
- A aba **Categorias** mostra desempenho por categoria.
- A aba **Cidades** mostra a distribuição geográfica das vendas.
- A aba **Clientes** mostra o ranking dos clientes.
- A aba **Canais** compara canais de venda e formas de pagamento.
- A aba **Avaliações** apresenta a distribuição das notas e a avaliação média por produto.
- A aba **Tendências** mostra a evolução mensal dos dados.
- A aba **Relatório** gera um resumo executivo e permite baixar o relatório em HTML e os dados filtrados em CSV.
- A aba **Dados** exibe a tabela completa dos registros filtrados.

## Observações importantes
- O gráfico de tendências usa a frequência mensal correta `ME` para evitar erro de resample.
- Os campos `data` e `cliente` são tratados automaticamente para evitar valores inválidos como `None`.
- Se você alterar os dados no MongoDB, basta atualizar a página do Streamlit para recarregar as informações.

## Se der erro
- Verifique se o MongoDB está aberto.
- Confirme se a coleção existe em `base.vendas`.
- Verifique se os pacotes do projeto estão instalados.
- Se o navegador mostrar uma tela antiga, recarregue a página.

## Estrutura principal
- `projeto_final.py`: aplicação principal do dashboard
- `app.py`: outra versão da aplicação, caso você queira comparar ou reaproveitar partes do código
- `requirements.txt`: lista de dependências do projeto

## Fluxo recomendado
1. Inicie o MongoDB local.
2. Execute a aplicação com Streamlit.
3. Aplique os filtros necessários.
4. Consulte os gráficos e a aba de relatório.
5. Baixe o relatório ou o CSV filtrado se precisar compartilhar os resultados.
README.md
Exibindo requirements.txt.
