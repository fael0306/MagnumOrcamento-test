# Ambiente de teste

# Conteúdo completo do arquivo streamlit_app (1).py após as alterações
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import unicodedata
import math
import plotly.express as px
import plotly.graph_objects as go
import uuid
import io
import reportlab
import re
import unicodedata

def sanitize_filename(filename: str) -> str:
    """
    Sanitiza um nome de arquivo, removendo caracteres perigosos e padronizando.
    - Converte para ASCII (remove acentos)
    - Substitui espaços e caracteres especiais por '_'
    - Permite apenas letras, números, '.', '-', '_'
    - Impede nomes vazios ou compostos apenas por '.'
    - Remove sequências '..' para evitar path traversal
    """
    if not filename:
        return "arquivo"

    # Normaliza para remover acentos e caracteres especiais
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ASCII', 'ignore').decode('ASCII')

    # Separa nome e extensão
    base, ext = os.path.splitext(filename)
    
    # Substitui caracteres não permitidos por '_'
    base = re.sub(r'[^\w\.\-]', '_', base)
    ext = re.sub(r'[^\w\.]', '', ext)  # extensão só pode ter letras, números e ponto

    # Remove underscores múltiplos
    base = re.sub(r'_+', '_', base).strip('_')
    ext = ext.strip('.')

    # Evita nomes perigosos como ".." ou vazios
    if not base or base in ('.', '..'):
        base = "arquivo"

    # Limita o tamanho do nome (opcional, evita nomes muito longos)
    max_len = 100
    if len(base) > max_len:
        base = base[:max_len]

    # Reconstrói nome com extensão (se houver)
    if ext:
        # Garante que a extensão comece com ponto
        return f"{base}.{ext.lower()}"
    else:
        return base

st.set_page_config(page_title="Magnum Engenharia", layout="wide")

# =========================================================
# LOGIN
# =========================================================
import bcrypt

# =========================================================
# LOGIN (com bcrypt)
# =========================================================
# =========================================================
# AUTENTICAÇÃO MULTI-USUÁRIO VIA SECRETS
# =========================================================
def autenticar(login, senha):
    """Retorna (autenticado, role, nome) ou (False, None, None)"""
    usuarios = st.secrets.get("usuarios", {})
    user_data = usuarios.get(login.strip())
    if not user_data:
        return False, None, None
    hash_salvo = user_data["senha_hash"]
    if bcrypt.checkpw(senha.strip().encode('utf-8'), hash_salvo.encode('utf-8')):
        role = user_data.get("role", "usuario")
        nome = user_data.get("nome", login)
        return True, role, nome
    return False, None, None

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:

    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(120deg, #f1f5f9, #e2e8f0);
    }
    .block-container {
        height: 100vh;
        display: flex;
        justify-content: center;
        flex-direction: column;
    }
    header, footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=200)
        st.write("Sistema de gestão de obras e financeiro")

    with col2:
        st.title("Entrar")

        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            auth, role, nome = autenticar(user, password)
            if auth:
                st.session_state.user = user
                st.session_state.role = role
                st.session_state.nome = nome
                st.rerun()
            else:
                st.error("Credenciais inválidas")

    st.stop()

# =========================================================
# LOGOUT
# =========================================================
if st.sidebar.button("Logout"):
    for key in ["user", "role", "nome"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# =========================================================
# STORAGE PADRÃO
# =========================================================
DATA_DIR = "data"
DIARIO_DIR = "assets/diario"
ORC_DIR = "assets/orcamentos"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DIARIO_DIR, exist_ok=True)
os.makedirs(ORC_DIR, exist_ok=True)

def load(file, cols):
    path = os.path.join(DATA_DIR, file)
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df if set(cols).issubset(df.columns) else pd.DataFrame(columns=cols)
    df = pd.DataFrame(columns=cols)
    df.to_csv(path, index=False)
    return df

def save(df, file):
    df.to_csv(os.path.join(DATA_DIR, file), index=False)

# =========================================================
# CONFIGURAÇÕES DE SEGURANÇA PARA UPLOADS
# =========================================================
MAX_IMAGE_SIZE_MB = 5
MAX_EXCEL_SIZE_MB = 10
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}

import mimetypes

def validate_uploaded_file(uploaded_file, allowed_extensions, max_size_mb, file_type_label="arquivo"):
    """
    Valida um arquivo enviado via st.file_uploader.
    Retorna (is_valid, error_message).
    """
    if uploaded_file is None:
        return False, "Nenhum arquivo enviado."

    # 1. Verificar tamanho (em bytes)
    file_size_bytes = uploaded_file.size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size_bytes > max_size_bytes:
        return False, f"Arquivo excede {max_size_mb} MB. Tamanho atual: {file_size_bytes / (1024*1024):.2f} MB."

    # 2. Verificar extensão do nome do arquivo
    filename = uploaded_file.name
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        return False, f"Extensão '{file_ext}' não permitida. Extensões aceitas: {', '.join(allowed_extensions)}."

    # 3. Verificar MIME type (pelo cabeçalho do arquivo)
    # O Streamlit fornece uploaded_file.type, que é baseado na extensão.
    # Para maior segurança, podemos ler os primeiros bytes e usar mimetypes.
    # Por simplicidade, usaremos a extensão mapeada para MIME types esperados.
    mime_type, _ = mimetypes.guess_type(filename)
    expected_mime_main = None
    if file_ext in ALLOWED_IMAGE_EXTENSIONS:
        expected_mime_main = "image"
    elif file_ext in ALLOWED_EXCEL_EXTENSIONS:
        expected_mime_main = "application"

    if mime_type is None or not mime_type.startswith(expected_mime_main):
        return False, f"Tipo de arquivo inválido (MIME: {mime_type}). Esperado um {file_type_label}."

    return True, ""

# =========================================================
# INIT DATA
# =========================================================
obras = load("obras.csv", ["Obra", "PercentualCaixa"])
fluxo = load("fluxo.csv", ["Data","Descricao","Categoria","Valor","Obra","Fornecedor"])
pessoas = load("pessoas.csv", ["Pessoa","Percentual"])
fechamento = load("fechamento.csv", ["Mes","Obra","Lucro"])
distribuicao = load("distribuicao.csv", ["Mes","Obra","Pessoa","Percentual","Valor"])
diario = load("diario.csv", ["Data","Obra","Descricao","Responsavel","Imagem"])
orcamentos = load("orcamentos.csv", ["ID","Obra","Total","Arquivo","Data"])
fornecedores = load("fornecedores.csv", ["Fornecedor","Contato","Telefone","Email","Observações"])
reembolsos = load("reembolsos.csv", ["ID","DataSolicitacao","Obra","Funcionario","Descricao","Valor","Status","DataPagamento"])
planejamento = load("planejamento.csv", ["Obra", "Categoria", "Valor"])

if "user" in st.session_state:
    st.sidebar.markdown(f"👤 **{st.session_state.get('nome', st.session_state.user)}**")
    st.sidebar.caption(f"🔒 Papel: {st.session_state.get('role', 'usuario')}")

# =========================================================
# FILTRO GLOBAL
# =========================================================
st.sidebar.markdown("## 📁 Filtro de Obra")

if not obras.empty:
    obra_filtro = st.sidebar.selectbox("Obra", ["Todas"] + list(obras["Obra"]))
else:
    obra_filtro = "Todas"

def filtrar(df):
    if obra_filtro != "Todas" and "Obra" in df.columns:
        return df[df["Obra"] == obra_filtro]
    return df

# =========================================================
# LUCRO MENSAL
# =========================================================
import unicodedata

def normalize_text(s):
    if pd.isna(s):
        return ""
    s = str(s).lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def lucro_mensal(df):
    if df.empty:
        return pd.DataFrame(columns=["Mes","Obra","Lucro"])

    df = df.copy()
    df["Valor_num"] = pd.to_numeric(df["Valor"], errors="coerce")
    df = df.dropna(subset=["Valor_num"])
    df["Valor"] = df["Valor_num"]

    df["Data_parsed"] = pd.to_datetime(df["Data"], errors="coerce")
    invalid_dates = df[df["Data_parsed"].isna()]
    if not invalid_dates.empty:
        st.error("Existem datas inválidas no fluxo financeiro. Corrija na aba 'Fluxo' antes de continuar.")
        return pd.DataFrame(columns=["Mes","Obra","Lucro"])  # ← retorna vazio, não para o app

    df["Data"] = df["Data_parsed"]
    df = df.dropna(subset=["Obra"])
    df["Mes"] = df["Data"].dt.to_period("M").astype(str)

    df["Categoria_norm"] = df["Categoria"].apply(normalize_text)
    df["Tipo"] = df["Categoria_norm"].map({"entrada": 1, "saida": -1})

    invalid_cats = df[df["Tipo"].isna()]
    if not invalid_cats.empty:
        st.error("Existem categorias inválidas no fluxo financeiro. Use apenas 'Entrada' ou 'Saída'.")
        return pd.DataFrame(columns=["Mes","Obra","Lucro"])

    lucro = df.groupby(["Mes","Obra"]).apply(lambda g: (g["Valor"] * g["Tipo"]).sum()).reset_index()
    lucro.columns = ["Mes","Obra","Lucro"]
    return lucro

# =========================================================
# MENU
# =========================================================
menu_opcoes = [
    "Dashboard","Obras","Fluxo","Pessoas",
    "Fechamento","Distribuição","Diário","Orçamentos","Fornecedores","Reembolsos",
    "Planejamento", "Importação", "Backup", "Relatório de Obra"
]

# Adiciona "Usuários" apenas para administradores
if st.session_state.get("role") == "admin":
    menu_opcoes.append("Usuários")

menu = st.sidebar.radio("Menu", menu_opcoes)
    
# =========================================================
# DASHBOARD ROBUSTO
# =========================================================
if menu == "Dashboard":

    st.title("📊 BI Central - Dashboard Executivo")

    df = lucro_mensal(fluxo)
    if df.empty:
        st.warning("Sem dados ainda")
        st.stop()

    # Filtros locais
    st.subheader("🔎 Filtros do Dashboard")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filtro_mes = st.multiselect("Meses", sorted(df["Mes"].unique()))
    with col_f2:
        filtro_obra = st.multiselect("Obras", sorted(df["Obra"].unique()))
    with col_f3:
        filtro_categoria = st.multiselect("Categoria", sorted(fluxo["Categoria"].unique()))
    with col_f4:
        faixa_valor = st.slider("Faixa de Valor", 
                                min_value=float(fluxo["Valor"].min() or 0), 
                                max_value=float(fluxo["Valor"].max() or 10000), 
                                value=(0.0, float(fluxo["Valor"].max() or 10000)))

    df_filtrado = df.copy()
    if filtro_mes:
        df_filtrado = df_filtrado[df_filtrado["Mes"].isin(filtro_mes)]
    if filtro_obra:
        df_filtrado = df_filtrado[df_filtrado["Obra"].isin(filtro_obra)]
    if filtro_categoria:
        obras_validas = fluxo[fluxo["Categoria"].isin(filtro_categoria)]["Obra"].unique()
        df_filtrado = df_filtrado[df_filtrado["Obra"].isin(obras_validas)]
    df_filtrado = df_filtrado[df_filtrado["Lucro"].between(faixa_valor[0], faixa_valor[1])]
    
    caixa_retido_total = distribuicao[distribuicao["Pessoa"] == "🏦 Caixa Empresa"]["Valor"].sum()
    
    # KPIs
    st.subheader("📌 Indicadores-Chave")
    col1, col2, col3, col4, col5, col6 = st.columns(6)  # mude para 6 colunas
    col1.metric("Obras", df_filtrado["Obra"].nunique())
    col2.metric("Lucro Total", f"R$ {df_filtrado['Lucro'].sum():,.2f}")
    if not df_filtrado.empty:
        col3.metric("Mês mais lucrativo", df_filtrado.loc[df_filtrado['Lucro'].idxmax()]['Mes'])
        col4.metric("Obra destaque", df_filtrado.groupby("Obra")["Lucro"].sum().idxmax())
    else:
        col3.metric("Mês mais lucrativo", "-")
        col4.metric("Obra destaque", "-")
    entradas_total = fluxo[fluxo["Categoria"]=="Entrada"]["Valor"].sum()
    saidas_total = fluxo[fluxo["Categoria"]=="Saída"]["Valor"].sum()
    col5.metric("Entradas vs Saídas", f"{entradas_total:,.2f} / {saidas_total:,.2f}")
    col6.metric("Caixa Retido (Acumulado)", f"R$ {caixa_retido_total:,.2f}")

    st.divider()

    # Gráficos interativos
    st.subheader("📈 Evolução Mensal")
    evolucao = df_filtrado.groupby("Mes")["Lucro"].sum().reset_index()
    st.plotly_chart(px.line(evolucao, x="Mes", y="Lucro", markers=True), use_container_width=True)

    st.subheader("🏆 Ranking de Obras")
    ranking = df_filtrado.groupby("Obra")["Lucro"].sum().reset_index().sort_values("Lucro", ascending=False)
    st.plotly_chart(px.bar(ranking, x="Lucro", y="Obra", orientation="h", text_auto=True), use_container_width=True)

    st.subheader("📊 Entradas vs Saídas por Obra")
    fluxo_group = fluxo.groupby(["Obra","Categoria"])["Valor"].sum().reset_index()
    st.plotly_chart(px.bar(fluxo_group, x="Obra", y="Valor", color="Categoria", barmode="stack"), use_container_width=True)

    st.subheader("👥 Distribuição do Lucro (incluindo caixa)")
    if not pessoas.empty:
        # Criar dataframe combinando pessoas + caixa
        pessoas_plot = pessoas.copy()
        # Obter percentual médio de caixa das obras (ou usar um valor agregado)
        # Para simplificar, usaremos a média dos percentuais de caixa por obra (ponderado pelo lucro talvez)
        # Mas como o dashboard é geral, podemos mostrar apenas a distribuição entre pessoas.
        # Uma alternativa é calcular o caixa total retido a partir das distribuições já salvas.
        caixa_total = distribuicao[distribuicao["Pessoa"] == "🏦 Caixa Empresa"]["Valor"].sum()
        distribuido_pessoas = distribuicao[distribuicao["Pessoa"] != "🏦 Caixa Empresa"]["Valor"].sum()
        total_distribuido = caixa_total + distribuido_pessoas
        
        if total_distribuido > 0:
            plot_df = pd.DataFrame({
                "Destino": ["Caixa Empresa"] + list(pessoas["Pessoa"]),
                "Valor": [caixa_total] + [0]*len(pessoas)  # depois preencher
            })
            # Preencher valores das pessoas
            for i, pessoa in enumerate(pessoas["Pessoa"]):
                val = distribuicao[distribuicao["Pessoa"] == pessoa]["Valor"].sum()
                plot_df.loc[plot_df["Destino"] == pessoa, "Valor"] = val
            st.plotly_chart(px.pie(plot_df, names="Destino", values="Valor", title="Distribuição Acumulada"), use_container_width=True)
        else:
            st.info("Nenhuma distribuição realizada ainda.")

    st.subheader("📑 Orçamentos por Obra")
    if not orcamentos.empty:
        st.plotly_chart(px.treemap(orcamentos, path=["Obra"], values="Total"), use_container_width=True)

        st.divider()
        
    st.subheader("📉 Comparativo: Planejado x Realizado")

    # Carregar planejamento
    planejamento = load("planejamento.csv", ["Obra", "Categoria", "Valor"])
    
    if planejamento.empty:
        st.info("Nenhum planejamento cadastrado. Utilize a aba 'Planejamento' para definir orçamentos por categoria.")
    else:
        # Filtrar planejamento pelas obras selecionadas no filtro global (se não for "Todas")
        plan_filtrado = planejamento.copy()
        if obra_filtro != "Todas":
            plan_filtrado = plan_filtrado[plan_filtrado["Obra"] == obra_filtro]
        
        # Agrupar realizado a partir do fluxo financeiro
        realizado = fluxo.copy()
        realizado["Valor"] = pd.to_numeric(realizado["Valor"], errors="coerce")
        realizado = realizado.dropna(subset=["Valor", "Obra", "Categoria"])
        if obra_filtro != "Todas":
            realizado = realizado[realizado["Obra"] == obra_filtro]
        
        realizado_group = realizado.groupby(["Obra", "Categoria"])["Valor"].sum().reset_index()
        realizado_group = realizado_group.rename(columns={"Valor": "Realizado"})
        
        # Merge entre planejado e realizado
        comparativo = pd.merge(
            plan_filtrado,
            realizado_group,
            on=["Obra", "Categoria"],
            how="left"
        )
        comparativo["Realizado"] = comparativo["Realizado"].fillna(0)
        comparativo["Diferença"] = comparativo["Valor"] - comparativo["Realizado"]
        comparativo["% Executado"] = (comparativo["Realizado"] / comparativo["Valor"]) * 100
        comparativo["% Executado"] = comparativo["% Executado"].clip(0, 100)  # Evita valores >100%
        comparativo["Status"] = comparativo["Diferença"].apply(
            lambda x: "✅ Dentro" if x >= 0 else "🚨 Estouro"
        )
        
        # KPIs gerais
        total_planejado = comparativo["Valor"].sum()
        total_realizado = comparativo["Realizado"].sum()
        saldo_global = total_planejado - total_realizado
        perc_global = (total_realizado / total_planejado * 100) if total_planejado > 0 else 0
        
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        col_kpi1.metric("Total Planejado", f"R$ {total_planejado:,.2f}")
        col_kpi2.metric("Total Realizado", f"R$ {total_realizado:,.2f}")
        col_kpi3.metric("Saldo", f"R$ {saldo_global:,.2f}", 
                       delta_color="normal" if saldo_global >=0 else "inverse")
        col_kpi4.metric("% Executado", f"{perc_global:.1f}%")
        
        # Tabela detalhada com alertas
        # Exibir tabela formatada (sem estilo condicional complexo)
        st.subheader("📋 Detalhamento por Obra e Categoria")
        
        # Criar cópia para formatação de exibição
        comp_display = comparativo.copy()
        comp_display["Valor"] = comp_display["Valor"].apply(lambda x: f"R$ {x:,.2f}")
        comp_display["Realizado"] = comp_display["Realizado"].apply(lambda x: f"R$ {x:,.2f}")
        comp_display["Diferença"] = comp_display["Diferença"].apply(lambda x: f"R$ {x:,.2f}")
        comp_display["% Executado"] = comp_display["% Executado"].apply(lambda x: f"{x:.1f}%")
        
        # Reordenar colunas para melhor visualização
        colunas_ordem = ["Obra", "Categoria", "Valor", "Realizado", "Diferença", "% Executado", "Status"]
        comp_display = comp_display[colunas_ordem]
        
        st.dataframe(
            comp_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico de barras agrupadas (Planejado vs Realizado)
        st.subheader("📊 Visualização por Obra e Categoria")
        
        # Preparar dados para o gráfico (melt)
        comp_melt = comparativo.melt(
            id_vars=["Obra", "Categoria"], 
            value_vars=["Valor", "Realizado"],
            var_name="Tipo", 
            value_name="Montante"
        )
        comp_melt["Tipo"] = comp_melt["Tipo"].replace({"Valor": "Planejado", "Realizado": "Realizado"})
        
        fig = px.bar(
            comp_melt,
            x="Obra",
            y="Montante",
            color="Tipo",
            barmode="group",
            facet_col="Categoria",
            title="Planejado vs Realizado por Obra e Categoria",
            labels={"Montante": "Valor (R$)", "Obra": "Obra"},
            text_auto=True
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Alertas de estouro específicos
        estouros = comparativo[comparativo["Status"] == "🚨 Estouro"]
        if not estouros.empty:
            st.error("🚨 **Alertas de Estouro de Orçamento:**")
            for _, row in estouros.iterrows():
                st.write(f"- Obra **{row['Obra']}** - Categoria **{row['Categoria']}**: "
                         f"Planejado R$ {row['Valor']:,.2f} | Realizado R$ {row['Realizado']:,.2f} "
                         f"(Excedido em R$ {abs(row['Diferença']):,.2f})")
        else:
            st.success("✅ Nenhum estouro de orçamento detectado para os filtros atuais.")
    
    st.subheader("📒 Últimas Publicações")
    if not diario.empty:
        feed = diario.copy()
        feed["Data"] = pd.to_datetime(feed["Data"], errors="coerce")
        feed = feed.sort_values("Data", ascending=False).head(5)
        for _, row in feed.iterrows():
            st.markdown(f"**{row['Data'].date()} - {row['Obra']} ({row['Responsavel']})**: {row['Descricao']}")
    else:
        st.info("Nenhuma publicação registrada.")

    # Insights automáticos
    st.subheader("⚡ Insights")
    if df_filtrado["Lucro"].sum() < 0:
        st.error("🚨 Lucro negativo no período selecionado!")
    elif df_filtrado.empty:
        st.info("Nenhum dado disponível para os filtros selecionados.")
    else:
        obra_top = ranking.iloc[0]["Obra"] if not ranking.empty else "-"
        st.success(f"✅ Lucro positivo. Obra destaque: {obra_top}.")
        
    # =========================================================
    # NOVA SEÇÃO: ANÁLISE DETALHADA POR OBRA
    # =========================================================
    st.divider()
    st.subheader("🔍 Análise Detalhada por Obra")
    
    # Seleção da obra (independente do filtro global)
    lista_obras = sorted(obras["Obra"].unique()) if not obras.empty else []
    if not lista_obras:
        st.info("Cadastre obras para visualizar a análise detalhada.")
    else:
        obra_selecionada_detalhe = st.selectbox(
            "Escolha uma obra para análise detalhada:",
            options=lista_obras,
            key="detalhe_obra_select"
        )
        
        # Filtrar dados apenas da obra selecionada
        fluxo_obra = fluxo[fluxo["Obra"] == obra_selecionada_detalhe].copy()
        if fluxo_obra.empty:
            st.warning(f"Nenhum lançamento financeiro encontrado para a obra '{obra_selecionada_detalhe}'.")
        else:
            # Garantir coluna Valor numérica e data parseada
            fluxo_obra["Valor"] = pd.to_numeric(fluxo_obra["Valor"], errors="coerce")
            fluxo_obra = fluxo_obra.dropna(subset=["Valor"])
            fluxo_obra["Data"] = pd.to_datetime(fluxo_obra["Data"], errors="coerce")
            fluxo_obra = fluxo_obra.dropna(subset=["Data"])
            
            # Categorizar entrada e saída (usando normalização simples)
            fluxo_obra["Categoria_norm"] = fluxo_obra["Categoria"].apply(normalize_text)
            fluxo_obra["Tipo"] = fluxo_obra["Categoria_norm"].map({"entrada": "Receita", "saida": "Custo"})
            fluxo_obra = fluxo_obra.dropna(subset=["Tipo"])
            
            # Calcular receita total e custo total
            receita_total = fluxo_obra[fluxo_obra["Tipo"] == "Receita"]["Valor"].sum()
            custo_total = fluxo_obra[fluxo_obra["Tipo"] == "Custo"]["Valor"].sum()
            lucro_total = receita_total - custo_total
            margem = (lucro_total / receita_total * 100) if receita_total > 0 else 0.0
            
            # KPIs da obra
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            col_k1.metric("💰 Receita Total", f"R$ {receita_total:,.2f}")
            col_k2.metric("📉 Custo Total", f"R$ {custo_total:,.2f}")
            col_k3.metric("📊 Lucro", f"R$ {lucro_total:,.2f}")
            col_k4.metric("📈 Margem", f"{margem:.1f}%")
            
            st.divider()
            
            # Evolução mensal (Receita, Custo, Lucro)
            st.subheader("📅 Evolução Mensal")
            fluxo_obra["Mes"] = fluxo_obra["Data"].dt.to_period("M").astype(str)
            mensal = fluxo_obra.groupby(["Mes", "Tipo"])["Valor"].sum().unstack(fill_value=0).reset_index()
            # Garantir colunas 'Receita' e 'Custo' existam
            if "Receita" not in mensal.columns:
                mensal["Receita"] = 0
            if "Custo" not in mensal.columns:
                mensal["Custo"] = 0
            mensal["Lucro"] = mensal["Receita"] - mensal["Custo"]
            
            # Gráfico de linhas
            fig_evol = go.Figure()
            fig_evol.add_trace(go.Scatter(x=mensal["Mes"], y=mensal["Receita"],
                                          mode='lines+markers', name='Receita'))
            fig_evol.add_trace(go.Scatter(x=mensal["Mes"], y=mensal["Custo"],
                                          mode='lines+markers', name='Custo'))
            fig_evol.add_trace(go.Scatter(x=mensal["Mes"], y=mensal["Lucro"],
                                          mode='lines+markers', name='Lucro'))
            fig_evol.update_layout(xaxis_title="Mês", yaxis_title="Valor (R$)")
            st.plotly_chart(fig_evol, use_container_width=True)
            
            st.divider()
            
            # Comparação com orçamento planejado
            st.subheader("📋 Planejado vs Realizado por Categoria")
            planejamento = load("planejamento.csv", ["Obra", "Categoria", "Valor"])
            plan_obra = planejamento[planejamento["Obra"] == obra_selecionada_detalhe].copy()
            
            if plan_obra.empty:
                st.info("Nenhum planejamento cadastrado para esta obra.")
            else:
                # Agrupar realizado por categoria (usando categoria original do fluxo)
                realizado_cat = fluxo_obra.groupby("Categoria")["Valor"].sum().reset_index()
                realizado_cat = realizado_cat.rename(columns={"Valor": "Realizado"})
                
                # Mesclar com planejado
                comparativo = pd.merge(plan_obra, realizado_cat, on="Categoria", how="left")
                comparativo["Realizado"] = comparativo["Realizado"].fillna(0)
                comparativo["Diferença"] = comparativo["Valor"] - comparativo["Realizado"]
                comparativo["% Executado"] = (comparativo["Realizado"] / comparativo["Valor"]) * 100
                comparativo["% Executado"] = comparativo["% Executado"].clip(0, 100)
                comparativo["Status"] = comparativo["Diferença"].apply(
                    lambda x: "✅ Dentro" if x >= 0 else "🚨 Estouro"
                )
                
                # Exibir tabela resumida
                st.dataframe(
                    comparativo[["Categoria", "Valor", "Realizado", "Diferença", "% Executado", "Status"]]
                    .style.format({
                        "Valor": "R$ {:,.2f}",
                        "Realizado": "R$ {:,.2f}",
                        "Diferença": "R$ {:,.2f}",
                        "% Executado": "{:.1f}%"
                    }),
                    use_container_width=True
                )
                
                # Gráfico de barras planejado vs realizado
                comp_melt = comparativo.melt(
                    id_vars="Categoria", 
                    value_vars=["Valor", "Realizado"],
                    var_name="Tipo", 
                    value_name="Montante"
                )
                comp_melt["Tipo"] = comp_melt["Tipo"].replace({"Valor": "Planejado", "Realizado": "Realizado"})
                fig_comp = px.bar(
                    comp_melt, x="Categoria", y="Montante", color="Tipo", barmode="group",
                    title="Planejado vs Realizado por Categoria",
                    text_auto=True
                )
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # Alertas de estouro
                estouros = comparativo[comparativo["Status"] == "🚨 Estouro"]
                if not estouros.empty:
                    st.error("🚨 Categorias com estouro de orçamento:")
                    for _, row in estouros.iterrows():
                        st.write(f"- **{row['Categoria']}**: Planejado R$ {row['Valor']:,.2f} | Realizado R$ {row['Realizado']:,.2f} (excedido em R$ {abs(row['Diferença']):,.2f})")
                else:
                    st.success("✅ Nenhum estouro de orçamento para esta obra.")

# =========================================================
# OBRAS
# =========================================================
elif menu == "Obras":
    st.title("Obras")
    
    # Editor de dados para obras existentes
    st.subheader("📋 Editar obras e percentual de caixa")
    edited_obras = st.data_editor(
        obras,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Obra": st.column_config.TextColumn("Obra", required=True),
            "PercentualCaixa": st.column_config.NumberColumn(
                "Caixa (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f %%",
                help="Percentual do lucro que fica retido no caixa da empresa"
            )
        }
    )
    
    if st.button("💾 Salvar alterações"):
        # Validar nomes únicos (não vazios)
        if edited_obras["Obra"].isnull().any() or (edited_obras["Obra"] == "").any():
            st.error("O nome da obra não pode ser vazio.")
        elif not edited_obras["Obra"].is_unique:
            st.error("Existem obras com nomes duplicados.")
        else:
            obras = edited_obras
            save(obras, "obras.csv")
            st.success("Obras atualizadas com sucesso!")
            st.rerun()

# =========================================================
# FLUXO
# =========================================================
elif menu == "Fluxo":
    st.title("Fluxo Financeiro")

    # --- Formulário para novo lançamento ---
    with st.expander("➕ Novo lançamento", expanded=False):
        tipo = st.selectbox("Categoria", ["Entrada", "Saída"])
        fornecedores = load("fornecedores.csv", ["Fornecedor","Contato","Telefone","Email","Observações"])
        with st.form("fluxo_form"):
            data = st.date_input("Data")
            obra = st.selectbox("Obra", obras["Obra"] if not obras.empty else [])
            valor = st.number_input("Valor", min_value=0.0)
            desc = st.text_input("Descrição")
            fornecedor = st.selectbox("Fornecedor (opcional)", [""] + list(fornecedores["Fornecedor"]))
            if st.form_submit_button("Salvar"):
                if obra not in obras["Obra"].values:
                    st.error("Obra inválida.")
                else:
                    novo = pd.DataFrame([{
                        "Data": data,
                        "Descricao": desc,
                        "Categoria": tipo,
                        "Valor": valor,
                        "Obra": obra,
                        "Fornecedor": fornecedor
                    }])
                    fluxo = pd.concat([fluxo, novo], ignore_index=True)
                    save(fluxo, "fluxo.csv")
                    st.success("Lançamento adicionado!")
                    st.rerun()

    st.divider()

    # --- Ferramentas de correção de datas ---
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🛠️ Corrigir todas as datas (remover horas)"):
            fluxo["Data"] = pd.to_datetime(fluxo["Data"], errors="coerce").dt.date
            fluxo = fluxo.dropna(subset=["Data"])
            save(fluxo, "fluxo.csv")
            st.success("Datas corrigidas com sucesso!")
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Limpar linhas com data inválida"):
            fluxo["Data"] = pd.to_datetime(fluxo["Data"], errors="coerce").dt.date
            before = len(fluxo)
            fluxo = fluxo.dropna(subset=["Data"])
            after = len(fluxo)
            save(fluxo, "fluxo.csv")
            st.success(f"Removidas {before - after} linhas com data inválida.")
            st.rerun()

    # --- Editor de dados (tabela editável) ---
    st.subheader("📋 Lançamentos (edite diretamente na tabela)")

    df_edit = filtrar(fluxo).copy()
    if df_edit.empty:
        st.info("Nenhum lançamento para exibir.")
    else:
        # Garantir tipos corretos para o editor
        df_edit["Data"] = pd.to_datetime(df_edit["Data"], errors="coerce").dt.date
        df_edit["Categoria"] = df_edit["Categoria"].str.strip()
        df_edit["Fornecedor"] = df_edit["Fornecedor"].fillna("").astype(str)

        edited_df = st.data_editor(
            df_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Categoria": st.column_config.SelectboxColumn(
                    "Categoria",
                    options=["Entrada", "Saída"],
                    required=True,
                ),
                "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD"),
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            },
            key="fluxo_editor"
        )

        col_save, col_delete = st.columns(2)
        with col_save:
            if st.button("💾 Salvar alterações"):
                fluxo_original = load("fluxo.csv", ["Data","Descricao","Categoria","Valor","Obra","Fornecedor"])
                if obra_filtro != "Todas":
                    fluxo_outras = fluxo_original[fluxo_original["Obra"] != obra_filtro]
                    fluxo_final = pd.concat([fluxo_outras, edited_df], ignore_index=True)
                else:
                    fluxo_final = edited_df
                # Converter Data para string antes de salvar
                fluxo_final["Data"] = pd.to_datetime(fluxo_final["Data"]).dt.date.astype(str)
                save(fluxo_final, "fluxo.csv")
                st.success("Alterações salvas com sucesso!")
                st.rerun()
        with col_delete:
            selected_indices = st.multiselect(
                "Selecione os índices das linhas que deseja excluir:",
                options=edited_df.index.tolist(),
                format_func=lambda x: f"Linha {x}"
            )
            if st.button("❌ Excluir linhas selecionadas"):
                if selected_indices:
                    edited_df = edited_df.drop(index=selected_indices)
                    fluxo_original = load("fluxo.csv", ["Data","Descricao","Categoria","Valor","Obra","Fornecedor"])
                    if obra_filtro != "Todas":
                        fluxo_outras = fluxo_original[fluxo_original["Obra"] != obra_filtro]
                        fluxo_final = pd.concat([fluxo_outras, edited_df], ignore_index=True)
                    else:
                        fluxo_final = edited_df
                    fluxo_final["Data"] = pd.to_datetime(fluxo_final["Data"]).dt.date.astype(str)
                    save(fluxo_final, "fluxo.csv")
                    st.success(f"{len(selected_indices)} linha(s) excluída(s).")
                    st.rerun()
                else:
                    st.warning("Nenhuma linha selecionada.")

# =========================================================
# PESSOAS
# =========================================================
elif menu == "Pessoas":

    st.title("Pessoas")

    edit = st.data_editor(pessoas, num_rows="dynamic")

    if st.button("Salvar"):
        edit["Percentual"] = pd.to_numeric(edit["Percentual"], errors="coerce").fillna(0)

        if not math.isclose(edit["Percentual"].sum(), 100, rel_tol=1e-9, abs_tol=1e-6):
            st.error("A soma dos percentuais deve ser 100%")
        else:
            pessoas = edit
            save(pessoas, "pessoas.csv")
            st.success("Pessoas salvas com sucesso!")


# =========================================================
# FECHAMENTO
# =========================================================
elif menu == "Fechamento":
    st.title("📊 Fechamento Mensal com Caixa")

    # Carregar dados existentes (se houver) – colunas: Mes, Obra, Lucro, Caixa
    fechamento = load("fechamento.csv", ["Mes", "Obra", "Lucro", "Caixa"])

    # Calcular disponibilidade de lucro no fluxo (para decidir se mostra botão de recalcular)
    tem_dados_fluxo = False
    try:
        df_lucro_temp = lucro_mensal(fluxo)
        tem_dados_fluxo = not df_lucro_temp.empty
    except:
        tem_dados_fluxo = False

    # Se o arquivo estiver vazio, calcular automaticamente a partir do fluxo
    if fechamento.empty:
        if tem_dados_fluxo:
            df_lucro = df_lucro_temp.merge(
                obras[["Obra", "PercentualCaixa"]],
                on="Obra",
                how="left"
            )
            df_lucro["PercentualCaixa"] = df_lucro["PercentualCaixa"].fillna(0)
            df_lucro["Caixa"] = df_lucro["Lucro"] * df_lucro["PercentualCaixa"] / 100.0
            fechamento = df_lucro[["Mes", "Obra", "Lucro", "Caixa"]]
            save(fechamento, "fechamento.csv")
            st.success("Fechamento gerado automaticamente a partir do fluxo financeiro.")
        else:
            st.info("Nenhum dado de lucro disponível no fluxo financeiro.")

    # --- Botão para recalcular tudo (apenas se houver dados) ---
    if tem_dados_fluxo:
        if st.button("🔄 Recalcular todo o fechamento (apagar atual e gerar novo)"):
            df_lucro = lucro_mensal(fluxo)
            if not df_lucro.empty:
                df_lucro = df_lucro.merge(
                    obras[["Obra", "PercentualCaixa"]],
                    on="Obra",
                    how="left"
                )
                df_lucro["PercentualCaixa"] = df_lucro["PercentualCaixa"].fillna(0)
                df_lucro["Caixa"] = df_lucro["Lucro"] * df_lucro["PercentualCaixa"] / 100.0
                novo_fechamento = df_lucro[["Mes", "Obra", "Lucro", "Caixa"]]
                save(novo_fechamento, "fechamento.csv")
                st.success("Fechamento recalculado com sucesso!")
                st.rerun()
            else:
                st.warning("Não há dados de lucro para recalcular.")

    # Aplicar filtro global por obra (sidebar)
    df_exibicao = filtrar(fechamento).copy()

    if df_exibicao.empty:
        st.warning("Nenhum registro de fechamento para exibir.")
        st.stop()

    # Tabela somente leitura com seleção múltipla
    st.subheader("📋 Registros de Fechamento (somente leitura)")
    event = st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row",
        on_select="rerun",
        key="fechamento_table"
    )

    selected_indices = event.selection.get("rows", [])

    if selected_indices:
        if st.button("🗑️ Excluir linhas selecionadas"):
            indices_originais = df_exibicao.index[selected_indices]
            fechamento = fechamento.drop(indices_originais).reset_index(drop=True)
            save(fechamento, "fechamento.csv")
            st.success(f"{len(selected_indices)} registro(s) excluído(s).")
            st.rerun()

    st.caption("ℹ️ Para corrigir um mês específico: ajuste os lançamentos no fluxo financeiro, depois exclua a linha correspondente aqui ou use o botão 'Recalcular' para refazer tudo.")

# =========================================================
# DISTRIBUIÇÃO
# =========================================================
elif menu == "Distribuição":
    st.title("Distribuição de Lucro por Obra")

    if obras.empty:
        st.warning("Cadastre obras primeiro.")
        st.stop()

    # ----- Cadastro de Pessoas (sempre visível) -----
    with st.expander("👥 Cadastro de Pessoas e Percentuais", expanded=False):
        edit = st.data_editor(pessoas, num_rows="dynamic", key="pessoas_editor")
        if st.button("Salvar Pessoas"):
            edit["Percentual"] = pd.to_numeric(edit["Percentual"], errors="coerce").fillna(0)
            if math.isclose(edit["Percentual"].sum(), 100, rel_tol=1e-9, abs_tol=1e-6):
                pessoas = edit
                save(pessoas, "pessoas.csv")
                st.success("Pessoas atualizadas com sucesso!")
            else:
                st.error("A soma dos percentuais deve ser 100%")

    # ----- Seleção da Obra -----
    obra_selecionada = st.selectbox("Selecione a obra para distribuir o lucro:", obras["Obra"])

    # Obter percentual de caixa da obra
    percentual_caixa = obras.loc[obras["Obra"] == obra_selecionada, "PercentualCaixa"].iloc[0]
    st.metric("Percentual de Caixa Retido", f"{percentual_caixa:.1f}%")

    # Calcular fechamento (lucro mensal)
    fechamento = lucro_mensal(fluxo)
    base_obra = fechamento[fechamento["Obra"] == obra_selecionada]
    if base_obra.empty:
        st.info(f"Não há dados financeiros para a obra '{obra_selecionada}'.")
        st.stop()

    # Escolher o mês
    meses_disponiveis = base_obra["Mes"].unique()
    mes_selecionado = st.selectbox("Selecione o mês:", meses_disponiveis)

    lucro_mes = base_obra[base_obra["Mes"] == mes_selecionado]["Lucro"].sum()
    
    # Cálculos de caixa
    valor_caixa = lucro_mes * (percentual_caixa / 100)
    valor_distribuivel = lucro_mes - valor_caixa

    col1, col2, col3 = st.columns(3)
    col1.metric("Lucro Total no Mês", f"R$ {lucro_mes:,.2f}")
    col2.metric("Valor Retido (Caixa)", f"R$ {valor_caixa:,.2f}", delta=f"{percentual_caixa:.1f}%")
    col3.metric("Valor a Distribuir", f"R$ {valor_distribuivel:,.2f}")

    if lucro_mes < 0:
        st.error("🚨 Lucro negativo. Não é possível distribuir.")
    elif valor_distribuivel <= 0:
        st.warning("Valor a distribuir é zero ou negativo. Nada a fazer.")
    else:
        if st.button(f"Distribuir lucro líquido de {mes_selecionado}"):
            # Remover distribuições antigas deste mês/obra
            distribuicao = distribuicao[
                ~((distribuicao["Mes"] == mes_selecionado) & (distribuicao["Obra"] == obra_selecionada))
            ]
            # Criar novas linhas com base no cadastro de pessoas usando o valor distribuível
            novas_linhas = []
            for _, pessoa in pessoas.iterrows():
                novas_linhas.append({
                    "Mes": mes_selecionado,
                    "Obra": obra_selecionada,
                    "Pessoa": pessoa["Pessoa"],
                    "Percentual": pessoa["Percentual"],
                    "Valor": valor_distribuivel * pessoa["Percentual"] / 100
                })
            # Adicionar linha do caixa (opcional, para registro)
            novas_linhas.append({
                "Mes": mes_selecionado,
                "Obra": obra_selecionada,
                "Pessoa": "🏦 Caixa Empresa",
                "Percentual": percentual_caixa,
                "Valor": valor_caixa
            })
            distribuicao = pd.concat([distribuicao, pd.DataFrame(novas_linhas)], ignore_index=True)
            save(distribuicao, "distribuicao.csv")
            st.success("Distribuição registrada com sucesso!")
            st.rerun()

    # ----- Exibir distribuições já realizadas para esta obra -----
    st.subheader("📋 Distribuições já realizadas")
    dist_obra = distribuicao[distribuicao["Obra"] == obra_selecionada]
    if dist_obra.empty:
        st.info("Nenhuma distribuição registrada para esta obra.")
    else:
        for mes in dist_obra["Mes"].unique():
            st.write(f"**Mês: {mes}**")
            df_mes = dist_obra[dist_obra["Mes"] == mes][["Pessoa", "Percentual", "Valor"]]
            # Destacar linha do caixa
            st.dataframe(df_mes, use_container_width=True, hide_index=True)
            st.divider()

# =========================================================
# DIÁRIO
# =========================================================
elif menu == "Diário":

    st.title("📒 Diário de Obra")

    # =========================================================
    # FORMULÁRIO (POST)
    # =========================================================
    with st.form("diario"):

        data = st.date_input("Data")
        obra = st.selectbox("Obra", obras["Obra"] if not obras.empty else [])
        resp = st.text_input("Responsável")
        desc = st.text_area("Descrição")
        img = st.file_uploader("Imagem", type=list(ALLOWED_IMAGE_EXTENSIONS))

        if st.form_submit_button("Publicar"):

            img_path = None
            if img is not None:
                is_valid, error_msg = validate_uploaded_file(img, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE_MB, "imagem")
                if not is_valid:
                    st.error(error_msg)
                    st.stop()  # impede o salvamento
            if img:
                import time
                safe_name = sanitize_filename(img.name)
                img_path = os.path.join(DIARIO_DIR, f"{time.time()}_{safe_name}")
                with open(img_path, "wb") as f:
                    f.write(img.read())

            novo = pd.DataFrame([{
                "Data": data,
                "Obra": obra,
                "Descricao": desc,
                "Responsavel": resp,
                "Imagem": img_path
            }])

            diario = pd.concat([diario, novo], ignore_index=True)
            save(diario, "diario.csv")

            st.rerun()

    st.divider()

    # =========================================================
    # FEED (REDE SOCIAL)
    # =========================================================
    st.subheader("📢 Feed das Obras")

    if diario.empty:
        st.info("Ainda não há publicações.")
    else:

        # mais recente primeiro
        feed = diario.copy()
        feed["Data"] = pd.to_datetime(feed["Data"], errors="coerce")
        feed = feed.sort_values("Data", ascending=False)

        for _, row in feed.iterrows():

            with st.container():

                col1, col2 = st.columns([1, 5])

                with col1:
                    st.markdown("🧑‍🔧")

                with col2:
                    st.markdown(f"""
### 🏗️ {row['Obra']}

**Responsável:** {row['Responsavel']}  
**Data:** {row['Data']}  

{row['Descricao']}
""")

                if pd.notna(row["Imagem"]) and os.path.exists(row["Imagem"]):
                    st.image(row["Imagem"], use_container_width=True)

                st.divider()


# =========================================================
# ORÇAMENTOS
# =========================================================
elif menu == "Orçamentos":

    st.title("📑 Orçamentos")

    fornecedores = load("fornecedores.csv", ["Fornecedor","Contato","Telefone","Email","Observações"])

    with st.form("orc"):

        obra = st.selectbox("Obra", obras["Obra"] if not obras.empty else [])
        total = st.number_input("Total")
        file = st.file_uploader("Arquivo Excel", type=list(ALLOWED_EXCEL_EXTENSIONS))
        fornecedor = st.selectbox("Fornecedor (opcional)", [""] + list(fornecedores["Fornecedor"]))

        if st.form_submit_button("Salvar") and file:
            is_valid, error_msg = validate_uploaded_file(file, ALLOWED_EXCEL_EXTENSIONS, MAX_EXCEL_SIZE_MB, "planilha Excel")
            if not is_valid:
                st.error(error_msg)
                st.stop()
            new_id = str(uuid.uuid4())
            safe_filename = sanitize_filename(file.name)
            name = f"orc_{new_id}_{safe_filename}"
            path = os.path.join(ORC_DIR, name)
        
            with open(path, "wb") as f:
                f.write(file.read())
        
            novo = pd.DataFrame([{
                "ID": new_id,
                "Obra": obra,
                "Total": total,
                "Arquivo": name,
                "Data": datetime.now(),
                "Fornecedor": fornecedor
            }])
        
            orcamentos = pd.concat([orcamentos, novo], ignore_index=True)
            save(orcamentos, "orcamentos.csv")
            st.success("Orçamento salvo com sucesso!")
            st.rerun()

    # --- Exibição da tabela com botão de download ---
    if not orcamentos.empty:
        st.subheader("📋 Orçamentos cadastrados")
        # Criar uma cópia para exibição, evitando modificar o original
        df_view = orcamentos.copy()
        # Garantir que a coluna Data seja datetime para formatação
        df_view["Data"] = pd.to_datetime(df_view["Data"], errors="coerce")
        df_view["Data"] = df_view["Data"].dt.strftime("%d/%m/%Y %H:%M")

        # Para cada linha, gerar um botão de download
        for idx, row in df_view.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2,2,2,2,2,1])
            with col1:
                st.write(row["Obra"])
            with col2:
                st.write(f"R$ {row['Total']:,.2f}")
            with col3:
                st.write(row["Fornecedor"] if pd.notna(row["Fornecedor"]) else "-")
            with col4:
                st.write(row["Data"])
            with col5:
                st.write(row["Arquivo"] if row["Arquivo"] else "-")
            with col6:
                arquivo = row["Arquivo"]
                if isinstance(arquivo, str) and arquivo.strip() != "":
                    caminho_arquivo = os.path.join(ORC_DIR, arquivo)
                    if os.path.exists(caminho_arquivo):
                        with open(caminho_arquivo, "rb") as f:
                            file_bytes = f.read()
                        st.download_button(
                            label="⬇️",
                            data=file_bytes,
                            file_name=arquivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_{row['ID']}"
                        )
                    else:
                        st.write("❌ (arquivo não encontrado)")
                else:
                    st.write("❌")
    else:
        st.info("Nenhum orçamento cadastrado.")

elif menu == "Fornecedores":
    st.title("Fornecedores / Prestadores de Serviço")

    edit = st.data_editor(fornecedores, num_rows="dynamic")

    if st.button("Salvar"):
        fornecedores = edit
        save(fornecedores, "fornecedores.csv")
        st.success("Dados salvos com sucesso!")
        st.rerun()

    st.dataframe(fornecedores)

elif menu == "Reembolsos":
    import time
    st.title("🧾 Solicitações de Reembolso")

    # ----- Formulário de nova solicitação -----
    with st.form("novo_reembolso"):
        st.subheader("➕ Nova solicitação")
        col1, col2 = st.columns(2)
        with col1:
            data_sol = st.date_input("Data da solicitação")
            obra = st.selectbox("Obra", obras["Obra"] if not obras.empty else [])
            funcionario = st.text_input("Funcionário solicitante")
        with col2:
            valor = st.number_input("Valor a reembolsar", min_value=0.01, step=0.01)
            descricao = st.text_area("Descrição do gasto")
        
        if st.form_submit_button("Registrar solicitação"):
            novo = pd.DataFrame([{
                "ID": str(uuid.uuid4()),
                "DataSolicitacao": data_sol,
                "Obra": obra,
                "Funcionario": funcionario,
                "Descricao": descricao,
                "Valor": valor,
                "Status": "pendente",
                "DataPagamento": ""
            }])
            # Carregar do disco e concatenar
            reembolsos = load("reembolsos.csv", ["ID","DataSolicitacao","Obra","Funcionario","Descricao","Valor","Status","DataPagamento"])
            reembolsos = pd.concat([reembolsos, novo], ignore_index=True)
            save(reembolsos, "reembolsos.csv")
            st.success("Solicitação registrada (pendente).")
            time.sleep(0.5)
            st.rerun()

    st.divider()

    # ----- Lista de solicitações com ações -----
    st.subheader("📋 Solicitações pendentes e histórico")
    
    # Recarregar do disco forçando tipos string para evitar NaN
    reembolsos = load("reembolsos.csv", ["ID","DataSolicitacao","Obra","Funcionario","Descricao","Valor","Status","DataPagamento"])
    # Converter colunas que podem conter strings vazias para string explicitamente
    reembolsos["DataPagamento"] = reembolsos["DataPagamento"].fillna("").astype(str)
    reembolsos["Status"] = reembolsos["Status"].astype(str)
    
    if reembolsos.empty:
        st.info("Nenhuma solicitação de reembolso.")
        st.stop()

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filtro = st.multiselect("Status", ["pendente","pago"], default=["pendente","pago"])
    with col_f2:
        obra_filtro_reemb = st.selectbox("Obra", ["Todas"] + list(reembolsos["Obra"].unique()))
    
    df_view = reembolsos[reembolsos["Status"].isin(status_filtro)]
    if obra_filtro_reemb != "Todas":
        df_view = df_view[df_view["Obra"] == obra_filtro_reemb]

    # Exibição com possibilidade de marcar como pago
    for _, row in df_view.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([3,1,1])
            with col1:
                st.markdown(f"""
                **{row['Funcionario']}** · {row['Obra']}  
                {row['Descricao']}  
                💰 R$ {row['Valor']:.2f} · 📅 {row['DataSolicitacao']}
                """)
            with col2:
                st.write(f"**Status:** {row['Status']}")
            with col3:
                if row["Status"] == "pendente":
                    if st.button("✅ Marcar como Pago", key=f"pagar_{row['ID']}"):
                        # Recarregar os dados do disco (garantindo estado fresco)
                        reembolsos_atual = load("reembolsos.csv", ["ID","DataSolicitacao","Obra","Funcionario","Descricao","Valor","Status","DataPagamento"])
                        # Converter DataPagamento para string para evitar problemas de tipo
                        reembolsos_atual["DataPagamento"] = reembolsos_atual["DataPagamento"].fillna("").astype(str)
                        
                        # Encontrar a linha com o ID correspondente
                        mask = reembolsos_atual["ID"] == row["ID"]
                        if mask.any():
                            # Atualizar os campos
                            reembolsos_atual.loc[mask, "Status"] = "pago"
                            reembolsos_atual.loc[mask, "DataPagamento"] = datetime.now().strftime("%Y-%m-%d")
                        else:
                            st.error("Registro não encontrado!")
                            st.stop()
                        
                        # Carregar fluxo atual e adicionar saída
                        fluxo_atual = load("fluxo.csv", ["Data","Descricao","Categoria","Valor","Obra","Fornecedor"])
                        nova_saida = pd.DataFrame([{
                            "Data": datetime.now().date(),
                            "Descricao": f"Reembolso pago a {row['Funcionario']}: {row['Descricao']}",
                            "Categoria": "Saída",
                            "Valor": row["Valor"],
                            "Obra": row["Obra"],
                            "Fornecedor": ""
                        }])
                        fluxo_atual = pd.concat([fluxo_atual, nova_saida], ignore_index=True)
                        
                        # Salvar ambos
                        save(reembolsos_atual, "reembolsos.csv")
                        save(fluxo_atual, "fluxo.csv")
                        
                        st.success("Reembolso pago e registrado no fluxo financeiro.")
                        time.sleep(1)
                        st.rerun()
            st.divider()

elif menu == "Planejamento":
    st.title("📊 Planejamento Orçamentário por Categoria")
    
    # ----- Formulário para adicionar/editar planejamento -----
    with st.expander("➕ Adicionar / Editar Planejamento", expanded=True):
        obra_sel = st.selectbox("Obra", obras["Obra"] if not obras.empty else [])
        categoria_sel = st.selectbox("Categoria", ["Entrada", "Saída"])
        valor_planejado = st.number_input("Valor Planejado", min_value=0.0, step=100.0)
        
        if st.button("Salvar Planejamento"):
            # Remove entrada antiga se existir (para evitar duplicatas)
            planejamento = load("planejamento.csv", ["Obra", "Categoria", "Valor"])
            planejamento = planejamento[
                ~((planejamento["Obra"] == obra_sel) & (planejamento["Categoria"] == categoria_sel))
            ]
            novo = pd.DataFrame([{
                "Obra": obra_sel,
                "Categoria": categoria_sel,
                "Valor": valor_planejado
            }])
            planejamento = pd.concat([planejamento, novo], ignore_index=True)
            save(planejamento, "planejamento.csv")
            st.success("Planejamento salvo!")
            st.rerun()
    
    # ----- Exibição da tabela de planejamento atual -----
    st.subheader("📋 Planejamentos Cadastrados")
    planejamento = load("planejamento.csv", ["Obra", "Categoria", "Valor"])
    if not planejamento.empty:
        # Opção de excluir
        for idx, row in planejamento.iterrows():
            col1, col2, col3, col4 = st.columns([3,2,2,1])
            with col1:
                st.write(row["Obra"])
            with col2:
                st.write(row["Categoria"])
            with col3:
                st.write(f"R$ {row['Valor']:,.2f}")
            with col4:
                if st.button("❌", key=f"del_plan_{idx}"):
                    planejamento = planejamento.drop(idx)
                    save(planejamento, "planejamento.csv")
                    st.rerun()
    else:
        st.info("Nenhum planejamento cadastrado.")

elif menu == "Importação":
    st.title("📥 Importação de Dados via Excel")
    st.markdown("Importe dados em massa para **Fluxo Financeiro**, **Orçamentos** ou **Planejamento**. Baixe o template correspondente, preencha e faça o upload.")

    tipo_import = st.selectbox("Selecione o tipo de dado para importar:", ["Fluxo Financeiro", "Orçamentos", "Planejamento"])

    # Função para gerar template
    def get_template_bytes(tipo):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if tipo == "Fluxo Financeiro":
                df_exemplo = pd.DataFrame({
                    "Data": ["2025-01-15", "2025-01-20"],
                    "Descricao": ["Compra de material", "Pagamento de medição"],
                    "Categoria": ["Saída", "Entrada"],
                    "Valor": [1500.00, 5000.00],
                    "Obra": ["Obra A", "Obra B"],
                    "Fornecedor": ["Fornecedor X", ""]
                })
                df_exemplo.to_excel(writer, index=False, sheet_name="Fluxo")
            elif tipo == "Orçamentos":
                df_exemplo = pd.DataFrame({
                    "Obra": ["Obra A", "Obra B"],
                    "Total": [12500.50, 8300.00],
                    "Fornecedor": ["Construtora Y", "Eletricista Z"]
                })
                df_exemplo.to_excel(writer, index=False, sheet_name="Orcamentos")
            elif tipo == "Planejamento":
                df_exemplo = pd.DataFrame({
                    "Obra": ["Obra A", "Obra A"],
                    "Categoria": ["Entrada", "Saída"],
                    "Valor": [50000.0, 30000.0]
                })
                df_exemplo.to_excel(writer, index=False, sheet_name="Planejamento")
        return output.getvalue()

    # Botões de download dos templates
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="⬇️ Baixar Template Fluxo",
            data=get_template_bytes("Fluxo Financeiro"),
            file_name="template_fluxo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col2:
        st.download_button(
            label="⬇️ Baixar Template Orçamentos",
            data=get_template_bytes("Orçamentos"),
            file_name="template_orcamentos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col3:
        st.download_button(
            label="⬇️ Baixar Template Planejamento",
            data=get_template_bytes("Planejamento"),
            file_name="template_planejamento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()

    uploaded_file = st.file_uploader("Escolha o arquivo Excel", type=["xlsx", "xls"])

    if uploaded_file is not None:
        is_valid, error_msg = validate_uploaded_file(uploaded_file, ALLOWED_EXCEL_EXTENSIONS, MAX_EXCEL_SIZE_MB, "planilha Excel")
        if not is_valid:
            st.error(error_msg)
            st.stop()
        try:
            df_import = pd.read_excel(uploaded_file, engine='openpyxl' if uploaded_file.name.endswith('.xlsx') else 'xlrd')
            st.subheader("📋 Pré-visualização dos dados")
            st.dataframe(df_import.head(10))

            if st.button("✅ Confirmar importação"):
                if tipo_import == "Fluxo Financeiro":
                    # Validações
                    required_cols = ["Data", "Descricao", "Categoria", "Valor", "Obra"]
                    missing = [col for col in required_cols if col not in df_import.columns]
                    if missing:
                        st.error(f"Colunas obrigatórias faltando: {missing}")
                        st.stop()

                    # Validar datas e remover horário
                    df_import["Data"] = pd.to_datetime(df_import["Data"], errors="coerce").dt.date
                    if df_import["Data"].isna().any():
                        st.error("Existem datas inválidas. Use o formato AAAA-MM-DD.")
                        st.stop()

                    # Validar valores numéricos
                    df_import["Valor"] = pd.to_numeric(df_import["Valor"], errors="coerce")
                    if df_import["Valor"].isna().any():
                        st.error("Existem valores não numéricos na coluna 'Valor'.")
                        st.stop()

                    # Validar categoria
                    categorias_validas = ["Entrada", "Saída"]
                    categorias_import = df_import["Categoria"].str.strip()
                    if not categorias_import.isin(categorias_validas).all():
                        st.error("A coluna 'Categoria' deve conter apenas 'Entrada' ou 'Saída'.")
                        st.stop()

                    # Validar se obras existem
                    obras_existentes = obras["Obra"].tolist()
                    obras_invalidas = df_import[~df_import["Obra"].isin(obras_existentes)]["Obra"].unique()
                    if len(obras_invalidas) > 0:
                        st.error(f"As seguintes obras não estão cadastradas: {', '.join(obras_invalidas)}")
                        st.stop()

                    # Adicionar coluna Fornecedor se não existir
                    if "Fornecedor" not in df_import.columns:
                        df_import["Fornecedor"] = ""

                    # Concatenar com fluxo existente (carregando do CSV mais recente)
                    fluxo_atual = load("fluxo.csv", ["Data","Descricao","Categoria","Valor","Obra","Fornecedor"])
                    novo_fluxo = pd.concat([fluxo_atual, df_import[["Data","Descricao","Categoria","Valor","Obra","Fornecedor"]]], ignore_index=True)
                    save(novo_fluxo, "fluxo.csv")
                    
                    # Atualizar estado global (opcional, mas garante que outras partes vejam o novo dado)
                    st.session_state["fluxo"] = novo_fluxo
                    
                    st.success(f"{len(df_import)} lançamentos importados com sucesso!")
                    st.balloons()

                elif tipo_import == "Orçamentos":
                    required_cols = ["Obra", "Total"]
                    missing = [col for col in required_cols if col not in df_import.columns]
                    if missing:
                        st.error(f"Colunas obrigatórias faltando: {missing}")
                        st.stop()

                    # Validar Total numérico
                    df_import["Total"] = pd.to_numeric(df_import["Total"], errors="coerce")
                    if df_import["Total"].isna().any():
                        st.error("Existem valores não numéricos na coluna 'Total'.")
                        st.stop()

                    # Validar obras existentes
                    obras_existentes = obras["Obra"].tolist()
                    obras_invalidas = df_import[~df_import["Obra"].isin(obras_existentes)]["Obra"].unique()
                    if len(obras_invalidas) > 0:
                        st.error(f"As seguintes obras não estão cadastradas: {', '.join(obras_invalidas)}")
                        st.stop()

                    # Salvar o arquivo Excel original (backup) na pasta de orçamentos
                    import time
                    timestamp = int(time.time())
                    safe_filename = sanitize_filename(uploaded_file.name)
                    arquivo_nome = f"orc_import_{timestamp}_{safe_filename}"
                    arquivo_path = os.path.join(ORC_DIR, arquivo_nome)
                    with open(arquivo_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())  # salva o conteúdo original

                    # Preparar dados para inserção
                    novos_orc = []
                    for _, row in df_import.iterrows():
                        new_id = str(uuid.uuid4())
                        novo = {
                            "ID": new_id,
                            "Obra": row["Obra"],
                            "Total": row["Total"],
                            "Arquivo": arquivo_nome,   # referência ao arquivo salvo
                            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Fornecedor": row.get("Fornecedor", "")
                        }
                        novos_orc.append(novo)

                    orc_atual = load("orcamentos.csv", ["ID","Obra","Total","Arquivo","Data"])
                    # Garantir que a coluna 'Fornecedor' exista no CSV carregado
                    if "Fornecedor" not in orc_atual.columns:
                        orc_atual["Fornecedor"] = ""
                    novo_orc = pd.concat([orc_atual, pd.DataFrame(novos_orc)], ignore_index=True)
                    save(novo_orc, "orcamentos.csv")
                    
                    st.session_state["orcamentos"] = novo_orc
                    
                    st.success(f"{len(novos_orc)} orçamentos importados com sucesso! Arquivo salvo como {arquivo_nome}")
                    st.balloons()

                elif tipo_import == "Planejamento":
                    required_cols = ["Obra", "Categoria", "Valor"]
                    missing = [col for col in required_cols if col not in df_import.columns]
                    if missing:
                        st.error(f"Colunas obrigatórias faltando: {missing}")
                        st.stop()

                    # Validar Valor numérico
                    df_import["Valor"] = pd.to_numeric(df_import["Valor"], errors="coerce")
                    if df_import["Valor"].isna().any():
                        st.error("Existem valores não numéricos na coluna 'Valor'.")
                        st.stop()

                    # Validar obras existentes
                    obras_existentes = obras["Obra"].tolist()
                    obras_invalidas = df_import[~df_import["Obra"].isin(obras_existentes)]["Obra"].unique()
                    if len(obras_invalidas) > 0:
                        st.error(f"As seguintes obras não estão cadastradas: {', '.join(obras_invalidas)}")
                        st.stop()

                    # Validar categorias
                    categorias_validas = ["Entrada", "Saída"]
                    cats_invalidas = df_import[~df_import["Categoria"].isin(categorias_validas)]["Categoria"].unique()
                    if len(cats_invalidas) > 0:
                        st.error(f"Categorias devem ser 'Entrada' ou 'Saída'. Inválidas: {', '.join(cats_invalidas)}")
                        st.stop()

                    # Substituir planejamento existente para as obras/categorias importadas
                    planejamento_atual = load("planejamento.csv", ["Obra", "Categoria", "Valor"])
                    # Remover registros que serão sobrescritos
                    chaves_import = df_import[["Obra", "Categoria"]].drop_duplicates()
                    for _, row in chaves_import.iterrows():
                        planejamento_atual = planejamento_atual[
                            ~((planejamento_atual["Obra"] == row["Obra"]) & 
                              (planejamento_atual["Categoria"] == row["Categoria"]))
                        ]
                    planejamento_novo = pd.concat([planejamento_atual, df_import], ignore_index=True)
                    save(planejamento_novo, "planejamento.csv")
                    st.success(f"{len(df_import)} registros de planejamento importados!")
                    st.rerun()

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")

elif menu == "Backup":
    st.title("💾 Backup Completo do Sistema")
    st.markdown("Gere um arquivo Excel contendo todas as tabelas do sistema. Escolha quais deseja incluir.")

    # Lista de tabelas disponíveis para exportação
    tabelas_disponiveis = {
        "Obras": obras,
        "Fluxo Financeiro": fluxo,
        "Pessoas": pessoas,
        "Fechamento Mensal": fechamento,
        "Distribuição de Lucro": distribuicao,
        "Diário de Obra": diario,
        "Orçamentos": orcamentos,
        "Fornecedores": fornecedores,
        "Reembolsos": reembolsos,
        "Planejamento": planejamento
    }

    # Checkboxes para seleção
    st.subheader("📌 Selecione as tabelas para incluir no backup:")
    selecionadas = {}
    cols = st.columns(2)
    for i, (nome, df) in enumerate(tabelas_disponiveis.items()):
        with cols[i % 2]:
            selecionadas[nome] = st.checkbox(f"{nome} ({len(df)} registros)", value=True)

    if st.button("📥 Gerar arquivo Excel para download"):
        tabelas_para_exportar = {nome: df for nome, df in tabelas_disponiveis.items() if selecionadas[nome]}

        if not tabelas_para_exportar:
            st.warning("Selecione pelo menos uma tabela para exportar.")
        else:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # ============================================================
                # NOVO: Adicionar aba de metadados (usuário + data/hora)
                # ============================================================
                metadados_df = pd.DataFrame([{
                    "Usuário": st.session_state.user,                     # quem está logado
                    "Data/Hora Backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Versão Sistema": "1.0"                                # opcional
                }])
                metadados_df.to_excel(writer, sheet_name="Metadados", index=False)

                # ============================================================
                # Escrever as tabelas selecionadas
                # ============================================================
                for nome, df in tabelas_para_exportar.items():
                    if df.empty:
                        pd.DataFrame({"Aviso": ["Nenhum dado cadastrado"]}).to_excel(writer, sheet_name=nome, index=False)
                    else:
                        df_export = df.copy()
                        for col in df_export.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                            df_export[col] = df_export[col].dt.strftime("%Y-%m-%d %H:%M:%S")
                        df_export.to_excel(writer, sheet_name=nome, index=False)

            output.seek(0)
            st.download_button(
                label="⬇️ Baixar Backup (Excel)",
                data=output,
                file_name=f"backup_magnum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Arquivo gerado com sucesso! Clique no botão acima para baixar.")
elif menu == "Usuários":
    st.title("👥 Usuários do Sistema")
    if st.session_state.get("role") != "admin":
        st.error("Acesso restrito a administradores.")
        st.stop()
    
    usuarios = st.secrets.get("usuarios", {})
    if not usuarios:
        st.info("Nenhum usuário definido nos secrets.")
    else:
        dados = []
        for login, info in usuarios.items():
            dados.append({
                "Login": login,
                "Nome": info.get("nome", ""),
                "Papel": info.get("role", "usuario"),
            })
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("ℹ️ A gestão de usuários é feita editando o arquivo `secrets.toml` e reimplantando o app (ou reiniciando localmente).")

# =========================================================
# RELATÓRIO DE OBRA (PDF)
# =========================================================
elif menu == "Relatório de Obra":
    st.title("📄 Relatório de Obra")
    st.markdown("Gere um relatório completo em PDF com resumo financeiro, KPIs, orçamentos e histórico do diário de obra.")

    # Seleção da obra
    if obras.empty:
        st.warning("Cadastre ao menos uma obra para gerar relatórios.")
        st.stop()

    obra_selecionada = st.selectbox("Selecione a obra para o relatório:", obras["Obra"].tolist())

    # Botão para gerar PDF
    if st.button("📑 Gerar Relatório PDF"):
        # Coletar dados da obra
        fluxo_obra = fluxo[fluxo["Obra"] == obra_selecionada].copy()
        diario_obra = diario[diario["Obra"] == obra_selecionada].copy()
        planejamento_obra = planejamento[planejamento["Obra"] == obra_selecionada].copy()
        orcamentos_obra = orcamentos[orcamentos["Obra"] == obra_selecionada].copy()

        # Processar dados financeiros
        if not fluxo_obra.empty:
            fluxo_obra["Valor"] = pd.to_numeric(fluxo_obra["Valor"], errors="coerce")
            fluxo_obra = fluxo_obra.dropna(subset=["Valor"])
            fluxo_obra["Data"] = pd.to_datetime(fluxo_obra["Data"], errors="coerce")
            fluxo_obra = fluxo_obra.dropna(subset=["Data"])

            # Normalizar categoria
            fluxo_obra["Categoria_norm"] = fluxo_obra["Categoria"].apply(normalize_text)
            fluxo_obra["Tipo"] = fluxo_obra["Categoria_norm"].map({"entrada": "Receita", "saida": "Custo"})
            fluxo_obra = fluxo_obra.dropna(subset=["Tipo"])

            receita_total = fluxo_obra[fluxo_obra["Tipo"] == "Receita"]["Valor"].sum()
            custo_total = fluxo_obra[fluxo_obra["Tipo"] == "Custo"]["Valor"].sum()
            lucro_total = receita_total - custo_total
            margem = (lucro_total / receita_total * 100) if receita_total > 0 else 0.0
        else:
            receita_total = custo_total = lucro_total = 0.0
            margem = 0.0

        # Planejado vs Realizado
        categorias_resumo = []
        if not planejamento_obra.empty:
            planejamento_obra["Valor"] = pd.to_numeric(planejamento_obra["Valor"], errors="coerce")
            realizado_cat = fluxo_obra.groupby("Categoria")["Valor"].sum().reset_index()
            realizado_cat = realizado_cat.rename(columns={"Valor": "Realizado"})
            comp = pd.merge(planejamento_obra, realizado_cat, on="Categoria", how="left")
            comp["Realizado"] = comp["Realizado"].fillna(0)
            comp["Diferença"] = comp["Valor"] - comp["Realizado"]
            comp["% Executado"] = (comp["Realizado"] / comp["Valor"]) * 100
            comp["% Executado"] = comp["% Executado"].clip(0, 100)
            categorias_resumo = comp.to_dict("records")
        else:
            categorias_resumo = []

        # Histórico do diário
        if not diario_obra.empty:
            diario_obra["Data"] = pd.to_datetime(diario_obra["Data"], errors="coerce")
            diario_obra = diario_obra.sort_values("Data", ascending=False).head(20)
            eventos = diario_obra[["Data", "Responsavel", "Descricao"]].to_dict("records")
        else:
            eventos = []

        # Orçamentos da obra
        if not orcamentos_obra.empty:
            # Ordenar por data decrescente e formatar colunas
            orcamentos_obra["Data"] = pd.to_datetime(orcamentos_obra["Data"], errors="coerce")
            orcamentos_obra = orcamentos_obra.sort_values("Data", ascending=False)
            orcamentos_lista = orcamentos_obra[["Data", "Fornecedor", "Total", "Arquivo"]].to_dict("records")
        else:
            orcamentos_lista = []

        # Informações adicionais
        percentual_caixa = obras.loc[obras["Obra"] == obra_selecionada, "PercentualCaixa"].iloc[0]
        data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Gerar PDF com reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Título
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=20,
            alignment=1,  # center
            spaceAfter=20
        )
        story.append(Paragraph(f"Relatório da Obra: {obra_selecionada}", title_style))
        story.append(Spacer(1, 0.5*cm))

        # Data de geração
        story.append(Paragraph(f"<i>Gerado em {data_geracao}</i>", styles['Normal']))
        story.append(Spacer(1, 1*cm))

        # Seção: Resumo Financeiro
        story.append(Paragraph("1. Resumo Financeiro", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        dados_financeiros = [
            ["Receita Total", f"R$ {receita_total:,.2f}"],
            ["Custo Total", f"R$ {custo_total:,.2f}"],
            ["Lucro Líquido", f"R$ {lucro_total:,.2f}"],
            ["Margem de Lucro", f"{margem:.1f}%"],
            ["% Caixa Retido", f"{percentual_caixa:.1f}%"],
            ["Valor Retido (Caixa)", f"R$ {lucro_total * percentual_caixa / 100:,.2f}"],
            ["Valor a Distribuir", f"R$ {lucro_total * (1 - percentual_caixa/100):,.2f}"]
        ]

        table_fin = Table(dados_financeiros, colWidths=[6*cm, 6*cm])
        table_fin.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table_fin)
        story.append(Spacer(1, 1*cm))

        # Seção: Planejado vs Realizado por Categoria
        if categorias_resumo:
            story.append(Paragraph("2. Planejado vs Realizado por Categoria", styles['Heading2']))
            story.append(Spacer(1, 0.3*cm))

            cabecalho = ["Categoria", "Planejado", "Realizado", "Diferença", "% Exec."]
            dados_cat = [cabecalho]
            for cat in categorias_resumo:
                dados_cat.append([
                    cat["Categoria"],
                    f"R$ {cat['Valor']:,.2f}",
                    f"R$ {cat['Realizado']:,.2f}",
                    f"R$ {cat['Diferença']:,.2f}",
                    f"{cat['% Executado']:.1f}%"
                ])

            table_cat = Table(dados_cat, colWidths=[3.5*cm, 3*cm, 3*cm, 3*cm, 2.5*cm])
            table_cat.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(table_cat)
            story.append(Spacer(1, 1*cm))
        else:
            story.append(Paragraph("2. Nenhum planejamento cadastrado para esta obra.", styles['Normal']))
            story.append(Spacer(1, 0.5*cm))

        # Seção: Orçamentos da Obra
        story.append(Paragraph("3. Orçamentos", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        if orcamentos_lista:
            cabecalho_orc = ["Data", "Fornecedor", "Total", "Arquivo"]
            dados_orc = [cabecalho_orc]
            for orc in orcamentos_lista:
                data_str = orc["Data"].strftime("%d/%m/%Y") if pd.notnull(orc["Data"]) else "-"
                fornecedor = orc["Fornecedor"] if orc["Fornecedor"] and str(orc["Fornecedor"]).strip() != "" else "-"
                total_str = f"R$ {orc['Total']:,.2f}" if pd.notnull(orc["Total"]) else "R$ 0,00"
                arquivo_str = orc["Arquivo"] if orc["Arquivo"] else "-"
                # Truncar nome do arquivo para não estourar a célula
                if len(arquivo_str) > 30:
                    arquivo_str = arquivo_str[:27] + "..."
                dados_orc.append([data_str, fornecedor, total_str, arquivo_str])

            table_orc = Table(dados_orc, colWidths=[2.5*cm, 4.5*cm, 3*cm, 5*cm])
            table_orc.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(table_orc)
        else:
            story.append(Paragraph("Nenhum orçamento cadastrado para esta obra.", styles['Normal']))

        story.append(Spacer(1, 1*cm))

        # Seção: Histórico do Diário de Obra
        story.append(Paragraph("4. Histórico de Eventos (últimas 20 entradas)", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        if eventos:
            dados_eventos = [["Data", "Responsável", "Descrição"]]
            for ev in eventos:
                dados_eventos.append([
                    ev["Data"].strftime("%d/%m/%Y") if pd.notnull(ev["Data"]) else "-",
                    ev["Responsavel"] if ev["Responsavel"] else "-",
                    ev["Descricao"][:80] + ("..." if len(ev["Descricao"]) > 80 else "")
                ])

            table_eventos = Table(dados_eventos, colWidths=[2.5*cm, 3.5*cm, 10*cm])
            table_eventos.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(table_eventos)
        else:
            story.append(Paragraph("Nenhum evento registrado no diário de obra.", styles['Normal']))

        # Rodapé
        story.append(Spacer(1, 1.5*cm))
        story.append(Paragraph("<i>Relatório gerado automaticamente pelo Sistema Magnum Engenharia</i>", styles['Italic']))

        # Construir PDF
        doc.build(story)
        buffer.seek(0)

        # Botão de download
        st.download_button(
            label="⬇️ Baixar Relatório PDF",
            data=buffer,
            file_name=f"relatorio_{obra_selecionada.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
        st.success("Relatório gerado com sucesso!")
