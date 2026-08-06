from pymongo import MongoClient
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title='Dashboard de Vendas NoSQL',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown(
    '''
    <style>
    .block-container { padding-top: 1.1rem; }
    </style>
    ''',
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def load_data():
    client = MongoClient('mongodb://localhost:27017/')
    df = pd.DataFrame(list(client['base']['vendas'].find()))
    if df.empty:
        return df

    if '_id' in df.columns:
        df['_id'] = df['_id'].astype(str)
    if 'data' in df.columns:
        # Normalize common empty markers and parse robustly
        df['data'] = df['data'].replace(['None', 'none', '', None], pd.NaT)
        df['data'] = pd.to_datetime(df['data'], errors='coerce', dayfirst=True)
    for col in ['preco', 'quantidade', 'avaliacao']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'preco' in df.columns and 'quantidade' in df.columns:
        df['total'] = df['preco'] * df['quantidade']
    elif 'preco' in df.columns:
        df['total'] = df['preco']
    else:
        df['total'] = 0

    # Normalize cliente names: strip whitespace, remove literal 'None'/'nan', title-case
    if 'cliente' in df.columns:
        tmp = df['cliente'].astype(str).str.strip()
        tmp = tmp.replace({'none': pd.NA, 'nan': pd.NA, '': pd.NA})
        tmp = tmp.where(tmp.notna(), pd.NA)
        df['cliente'] = tmp.apply(lambda x: x.title() if isinstance(x, str) else pd.NA)

    return df


def safe_groupby(df, group_col, value_col, agg='sum'):
    if group_col not in df.columns or value_col not in df.columns:
        return pd.Series(dtype=float)
    return df.groupby(group_col)[value_col].agg(agg).sort_values(ascending=False)


def as_money(value):
    return f'R$ {value:,.2f}'


def chart_bar_h(series, title, x_label, y_label, colorscale='Blues'):
    data = series.reset_index()
    data.columns = [y_label, x_label]
    fig = px.bar(
        data,
        x=x_label,
        y=y_label,
        orientation='h',
        title=title,
        color=x_label,
        color_continuous_scale=colorscale,
    )
    fig.update_layout(height=430, yaxis={'categoryorder': 'total ascending'})
    return fig


def chart_pie(series, title):
    fig = px.pie(
        names=series.index,
        values=series.values,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=430)
    return fig


def show_chart(fig, key):
    st.plotly_chart(fig, use_container_width=True, key=key)


def build_report_html(df, filtered):
    total_registros = len(filtered)
    total_unidades = int(filtered['quantidade'].sum()) if 'quantidade' in filtered.columns else 0
    total_receita = float(filtered['total'].sum()) if 'total' in filtered.columns else 0.0
    ticket_medio = total_receita / total_registros if total_registros else 0.0
    avaliacao_media = float(filtered['avaliacao'].mean()) if 'avaliacao' in filtered.columns and filtered['avaliacao'].notna().any() else 0.0

    def top_table(series, title):
        if series.empty:
            return f'<h3>{title}</h3><p>Sem dados.</p>'
        return f'<h3>{title}</h3>{series.head(10).to_frame().to_html(classes="table", border=0)}'

    parts = [
        '<html><head><meta charset="utf-8"><style>body{font-family:Arial,sans-serif;padding:24px;color:#111827} h1,h2,h3{margin:0.4rem 0} .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0} .card{border:1px solid #e5e7eb;border-radius:12px;padding:12px;background:#f9fafb} .table{border-collapse:collapse;width:100%;margin:8px 0 20px} .table th,.table td{border:1px solid #e5e7eb;padding:8px;text-align:left;font-size:13px} .table th{background:#f3f4f6}</style></head><body>',
        '<h1>Relatório Executivo de Vendas</h1>',
        '<p>Fonte: MongoDB base.vendas</p>',
        '<div class="grid">',
        f'<div class="card"><strong>Registros</strong><br>{total_registros}</div>',
        f'<div class="card"><strong>Unidades</strong><br>{total_unidades}</div>',
        f'<div class="card"><strong>Receita</strong><br>R$ {total_receita:,.2f}</div>',
        f'<div class="card"><strong>Ticket médio</strong><br>R$ {ticket_medio:,.2f}</div>',
        '</div>',
        f'<div class="grid"><div class="card"><strong>Avaliação média</strong><br>{avaliacao_media:.2f}</div><div class="card"><strong>Produtos</strong><br>{filtered["produto"].nunique() if "produto" in filtered.columns else 0}</div><div class="card"><strong>Cidades</strong><br>{filtered["cidade"].nunique() if "cidade" in filtered.columns else 0}</div><div class="card"><strong>Clientes</strong><br>{filtered["cliente"].nunique() if "cliente" in filtered.columns else 0}</div></div>',
    ]

    if 'categoria' in filtered.columns:
        cat_rev = safe_groupby(filtered, 'categoria', 'total')
        parts.append(top_table(cat_rev, 'Receita por categoria'))
    if 'cidade' in filtered.columns:
        city_qty = safe_groupby(filtered, 'cidade', 'quantidade')
        parts.append(top_table(city_qty, 'Quantidade por cidade'))
    if 'cliente' in filtered.columns:
        client_rev = safe_groupby(filtered, 'cliente', 'total')
        parts.append(top_table(client_rev, 'Receita por cliente'))
    if 'canal_venda' in filtered.columns:
        canal_rev = safe_groupby(filtered, 'canal_venda', 'total')
        parts.append(top_table(canal_rev, 'Receita por canal'))
    if 'forma_pagamento' in filtered.columns:
        pay_rev = safe_groupby(filtered, 'forma_pagamento', 'total')
        parts.append(top_table(pay_rev, 'Receita por forma de pagamento'))
    if 'avaliacao' in filtered.columns:
        av = pd.to_numeric(filtered['avaliacao'], errors='coerce').dropna().round().astype(int)
        av_counts = av.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
        parts.append(top_table(av_counts, 'Distribuição de avaliações'))

    if 'data' in filtered.columns:
        df_time = filtered.dropna(subset=['data'])
        if not df_time.empty:
            monthly = df_time.set_index('data').resample('ME').agg(
                quantidade=('quantidade', 'sum'),
                receita=('total', 'sum'),
            )
            parts.append('<h2>Tendências mensais</h2>')
            parts.append(monthly.head(12).to_html(classes="table", border=0))

    parts.append('<h2>Dados filtrados</h2>')
    parts.append(filtered.to_html(classes="table", border=0, index=False))
    parts.append('</body></html>')
    return ''.join(parts)


def main():
    df = load_data()
    st.title('📊 Dashboard Estratégico de Vendas')
    st.caption('Fonte: MongoDB `base.vendas` | base com mais de 2.000 registros')

    if df.empty:
        st.error('Nenhum documento encontrado em `base.vendas`.')
        return

    with st.sidebar:
        st.header('Filtros')

        categoria = st.selectbox('Categoria', ['Todas'] + sorted(df['categoria'].dropna().astype(str).unique().tolist())) if 'categoria' in df.columns else 'Todas'
        produto = st.selectbox('Produto', ['Todos'] + sorted(df['produto'].dropna().astype(str).unique().tolist())) if 'produto' in df.columns else 'Todos'
        cidade = st.selectbox('Cidade', ['Todas'] + sorted(df['cidade'].dropna().astype(str).unique().tolist())) if 'cidade' in df.columns else 'Todas'
        canal = st.selectbox('Canal de venda', ['Todos'] + sorted(df['canal_venda'].dropna().astype(str).unique().tolist())) if 'canal_venda' in df.columns else 'Todos'
        pagamento = st.selectbox('Forma de pagamento', ['Todos'] + sorted(df['forma_pagamento'].dropna().astype(str).unique().tolist())) if 'forma_pagamento' in df.columns else 'Todos'
        cliente = st.selectbox('Cliente', ['Todos'] + sorted(df['cliente'].dropna().astype(str).unique().tolist())) if 'cliente' in df.columns else 'Todos'

        if 'data' in df.columns:
            df_dates = df.dropna(subset=['data'])
            if not df_dates.empty:
                min_date = df_dates['data'].min().date()
                max_date = df_dates['data'].max().date()
                periodo = st.date_input('Período', value=(min_date, max_date), min_value=min_date, max_value=max_date)
            else:
                periodo = None
        else:
            periodo = None

    filtered = df.copy()
    if categoria != 'Todas':
        filtered = filtered[filtered['categoria'] == categoria]
    if produto != 'Todos':
        filtered = filtered[filtered['produto'] == produto]
    if cidade != 'Todas':
        filtered = filtered[filtered['cidade'] == cidade]
    if canal != 'Todos':
        filtered = filtered[filtered['canal_venda'] == canal]
    if pagamento != 'Todos':
        filtered = filtered[filtered['forma_pagamento'] == pagamento]
    if cliente != 'Todos':
        filtered = filtered[filtered['cliente'] == cliente]
    if periodo and isinstance(periodo, tuple) and len(periodo) == 2 and 'data' in filtered.columns:
        start, end = pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1])
        filtered = filtered[(filtered['data'].isna()) | ((filtered['data'] >= start) & (filtered['data'] <= end))]

    st.markdown('---')
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric('Registros', f'{len(filtered):,}')
    k2.metric('Unidades', f"{int(filtered['quantidade'].sum()) if 'quantidade' in filtered.columns else 0:,}")
    k3.metric('Receita', as_money(float(filtered['total'].sum())))
    k4.metric('Ticket médio', as_money(float(filtered['total'].sum()) / len(filtered)) if len(filtered) else 'R$ 0,00')
    k5.metric('Produtos', filtered['produto'].nunique() if 'produto' in filtered.columns else 0)
    k6.metric('Avaliação média', f"{filtered['avaliacao'].mean():.2f}" if 'avaliacao' in filtered.columns and filtered['avaliacao'].notna().any() else 'N/A')

    st.markdown('---')
    tabs = st.tabs(['Resumo', 'Produtos', 'Categorias', 'Cidades', 'Clientes', 'Canais', 'Avaliações', 'Tendências', 'Relatório', 'Dados'])

    # Resumo
    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader('Receita por categoria')
            cat_rev = safe_groupby(filtered, 'categoria', 'total')
            if not cat_rev.empty:
                show_chart(chart_bar_h(cat_rev, 'Receita por categoria', 'Receita (R$)', 'Categoria', 'Blues'), 'resumo_cat_receita')
            else:
                st.info('Sem dados de categoria.')
        with c2:
            st.subheader('Top 5 cidades por unidades')
            city_qty = safe_groupby(filtered, 'cidade', 'quantidade').head(5)
            if not city_qty.empty:
                show_chart(chart_pie(city_qty, 'Top 5 cidades por unidades'), 'resumo_city_pie')
            else:
                st.info('Sem dados de cidade.')

        st.subheader('Principais destaques')
        a, b, c = st.columns(3)
        a.info(f"Melhor categoria: {safe_groupby(filtered, 'categoria', 'total').idxmax() if not safe_groupby(filtered, 'categoria', 'total').empty else 'N/A'}")
        b.info(f"Melhor cidade: {safe_groupby(filtered, 'cidade', 'total').idxmax() if not safe_groupby(filtered, 'cidade', 'total').empty else 'N/A'}")
        c.info(f"Melhor produto: {safe_groupby(filtered, 'produto', 'total').idxmax() if not safe_groupby(filtered, 'produto', 'total').empty else 'N/A'}")

    # Produtos
    with tabs[1]:
        if 'produto' in filtered.columns:
            prod_stats = filtered.groupby('produto').agg(
                quantidade=('quantidade', 'sum'),
                receita=('total', 'sum'),
                preco_medio=('preco', 'mean'),
                avaliacao_media=('avaliacao', 'mean'),
            ).sort_values('receita', ascending=False)
            st.dataframe(prod_stats, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                top_qty = prod_stats.sort_values('quantidade', ascending=False).head(10)
                show_chart(
                    px.bar(top_qty.reset_index(), x='quantidade', y='produto', orientation='h', title='Top 10 produtos por quantidade', color='quantidade', color_continuous_scale='Tealgrn').update_layout(height=450, yaxis={'categoryorder': 'total ascending'}),
                    'produtos_top_quantidade',
                )
            with c2:
                top_rev = prod_stats.head(10)
                show_chart(
                    px.bar(top_rev.reset_index(), x='receita', y='produto', orientation='h', title='Top 10 produtos por receita', color='receita', color_continuous_scale='Oranges').update_layout(height=450, yaxis={'categoryorder': 'total ascending'}),
                    'produtos_top_receita',
                )
        else:
            st.info('Campo produto não existe.')

    # Categorias
    with tabs[2]:
        if 'categoria' in filtered.columns:
            cat_stats = filtered.groupby('categoria').agg(
                quantidade=('quantidade', 'sum'),
                receita=('total', 'sum'),
                preco_medio=('preco', 'mean'),
                avaliacao_media=('avaliacao', 'mean'),
            ).sort_values('receita', ascending=False)
            st.dataframe(cat_stats, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                show_chart(chart_bar_h(cat_stats['receita'], 'Receita por categoria', 'Receita (R$)', 'Categoria', 'Blues'), 'categorias_receita')
            with c2:
                show_chart(chart_bar_h(cat_stats['quantidade'], 'Quantidade por categoria', 'Unidades', 'Categoria', 'Viridis'), 'categorias_quantidade')
        else:
            st.info('Campo categoria não existe.')

    # Cidades
    with tabs[3]:
        if 'cidade' in filtered.columns:
            city_stats = filtered.groupby('cidade').agg(
                quantidade=('quantidade', 'sum'),
                receita=('total', 'sum'),
                clientes=('cliente', 'nunique'),
            ).sort_values('receita', ascending=False)
            st.dataframe(city_stats, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                show_chart(chart_bar_h(city_stats['receita'], 'Receita por cidade', 'Receita (R$)', 'Cidade', 'Purples'), 'cidades_receita')
            with c2:
                show_chart(chart_pie(city_stats.head(5)['quantidade'], 'Top 5 cidades por unidades'), 'cidades_pie')
        else:
            st.info('Campo cidade não existe.')

    # Clientes
    with tabs[4]:
        if 'cliente' in filtered.columns:
            client_stats = filtered.groupby('cliente').agg(
                quantidade=('quantidade', 'sum'),
                receita=('total', 'sum'),
                cidade=('cidade', 'first'),
                avaliacao_media=('avaliacao', 'mean'),
            ).sort_values('receita', ascending=False)
            st.dataframe(client_stats, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                show_chart(chart_bar_h(client_stats['receita'].head(10), 'Top 10 clientes por receita', 'Receita (R$)', 'Cliente', 'Oranges'), 'clientes_receita')
            with c2:
                show_chart(chart_bar_h(client_stats['quantidade'].sort_values(ascending=False).head(10), 'Top 10 clientes por unidades', 'Unidades', 'Cliente', 'Blues'), 'clientes_quantidade')
        else:
            st.info('Campo cliente não existe.')

    # Canais
    with tabs[5]:
        c1, c2 = st.columns(2)
        with c1:
            if 'canal_venda' in filtered.columns:
                canal_stats = filtered.groupby('canal_venda').agg(quantidade=('quantidade', 'sum'), receita=('total', 'sum')).sort_values('receita', ascending=False)
                st.dataframe(canal_stats, use_container_width=True)
                show_chart(chart_bar_h(canal_stats['receita'], 'Receita por canal', 'Receita (R$)', 'Canal', 'Blues'), 'canais_receita')
            else:
                st.info('Campo canal_venda não existe.')
        with c2:
            if 'forma_pagamento' in filtered.columns:
                pay_stats = filtered.groupby('forma_pagamento').agg(quantidade=('quantidade', 'sum'), receita=('total', 'sum')).sort_values('receita', ascending=False)
                st.dataframe(pay_stats, use_container_width=True)
                show_chart(chart_pie(pay_stats['receita'], 'Receita por forma de pagamento'), 'pagamentos_pie')
            else:
                st.info('Campo forma_pagamento não existe.')

    # Avaliações
    with tabs[6]:
        if 'avaliacao' in filtered.columns:
            if 'produto' in filtered.columns:
                rating_stats = filtered.groupby('produto').agg(
                    avaliacao_media=('avaliacao', 'mean'),
                    quantidade=('quantidade', 'sum'),
                    receita=('total', 'sum'),
                ).sort_values('avaliacao_media', ascending=False)
                st.dataframe(rating_stats, use_container_width=True)
                c1, c2 = st.columns(2)
                with c1:
                    top_rating = rating_stats.head(10)
                    fig = px.bar(top_rating.reset_index(), x='avaliacao_media', y='produto', orientation='h', title='Top 10 produtos por avaliação', color='avaliacao_media', color_continuous_scale='Purples')
                    fig.update_layout(height=450, xaxis_range=[0, 5], yaxis={'categoryorder': 'total ascending'})
                    show_chart(fig, 'avaliacoes_top_produtos')
                with c2:
                    # Mostrar contagem discreta por nota (1 a 5)
                    av = pd.to_numeric(filtered['avaliacao'], errors='coerce').dropna().round().astype(int)
                    counts = av.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0).reset_index()
                    counts.columns = ['avaliacao', 'count']
                    fig = px.bar(counts, x='avaliacao', y='count', title='Distribuição das avaliações', labels={'count': 'Contagem', 'avaliacao': 'Avaliação'}, color='avaliacao', color_continuous_scale=px.colors.sequential.Reds)
                    fig.update_layout(height=450, xaxis=dict(tickmode='array', tickvals=[1,2,3,4,5]))
                    show_chart(fig, 'avaliacoes_histograma')
            else:
                st.info('Campo produto não existe para cruzar com avaliação.')
        else:
            st.info('Campo avaliacao não existe.')

    # Tendências
    with tabs[7]:
        if 'data' in filtered.columns:
            df_time = filtered.dropna(subset=['data'])
            if df_time.empty:
                st.info('Sem datas válidas para tendência.')
            else:
                monthly = df_time.set_index('data').resample('ME').agg(
                    quantidade=('quantidade', 'sum'),
                    receita=('total', 'sum'),
                    ticket_medio=('total', 'mean'),
                    avaliacao_media=('avaliacao', 'mean'),
                )
                st.dataframe(monthly, use_container_width=True)
                c1, c2 = st.columns(2)
                with c1:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=monthly.index, y=monthly['quantidade'], mode='lines+markers', name='Quantidade'))
                    fig.update_layout(title='Quantidade mensal', height=420, yaxis_title='Unidades')
                    show_chart(fig, 'tendencias_quantidade')
                with c2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=monthly.index, y=monthly['receita'], mode='lines+markers', name='Receita'))
                    fig.update_layout(title='Receita mensal', height=420, yaxis_title='Receita (R$)')
                    show_chart(fig, 'tendencias_receita')
        else:
            st.info('Campo data não existe.')

    # Relatório
    with tabs[8]:
        st.subheader('Relatório executivo')
        st.write('Esta aba consolida as informações filtradas em um único relatório para download e consulta rápida.')
        report_html = build_report_html(df, filtered)
        st.download_button(
            'Baixar relatório HTML',
            data=report_html.encode('utf-8'),
            file_name='relatorio_vendas.html',
            mime='text/html',
        )
        st.download_button(
            'Baixar dados filtrados CSV',
            data=filtered.to_csv(index=False).encode('utf-8'),
            file_name='vendas_filtradas.csv',
            mime='text/csv',
        )
        with st.expander('Prévia do relatório'):
            st.markdown(f"""
            **Registros:** {len(filtered)}  
            **Unidades:** {int(filtered['quantidade'].sum()) if 'quantidade' in filtered.columns else 0}  
            **Receita:** {as_money(float(filtered['total'].sum()))}  
            **Ticket médio:** {as_money(float(filtered['total'].sum()) / len(filtered)) if len(filtered) else 'R$ 0,00'}
            """)
            st.dataframe(filtered.head(50), use_container_width=True)

    # Dados
    with tabs[9]:
        st.dataframe(filtered, use_container_width=True)
        st.download_button(
            'Baixar CSV filtrado',
            data=filtered.to_csv(index=False).encode('utf-8'),
            file_name='vendas_filtradas.csv',
            mime='text/csv',
        )


if __name__ == '__main__':
    main()
projeto_final.py
Exibindo requirements.txt.
