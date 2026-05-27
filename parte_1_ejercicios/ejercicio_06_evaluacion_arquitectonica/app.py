import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Evaluación Arquitecturas Big Data", layout="wide")

# --- DATOS CONSTANTES ---
NAMES = ['A — Local', 'B — Docker', 'C — Microservicios', 'D — Lakehouse', 'E — Cloud']
SHORT_NAMES = ['A', 'B', 'C', 'D', 'E']
COLORS = ['#888780', '#185FA5', '#1D9E75', '#BA7517', '#534AB7']
CRIT = [
    'Rendimiento', 'Costo relativo', 'Escalabilidad', 'Mantenibilidad', 
    'Reproducibilidad', 'Gobernanza', 'Seguridad', 'Resiliencia', 
    'Complejidad op. ↓', 'Madurez req. ↓'
]
INIT_W = [12, 15, 13, 10, 10, 8, 8, 8, 8, 8]
SCORES = [
    [2, 3, 3, 4, 5],  # Rendimiento
    [5, 4, 3, 2, 1],  # Costo relativo
    [1, 2, 3, 4, 5],  # Escalabilidad
    [3, 4, 3, 2, 3],  # Mantenibilidad
    [2, 5, 4, 3, 3],  # Reproducibilidad
    [2, 3, 3, 4, 5],  # Gobernanza
    [2, 3, 3, 4, 5],  # Seguridad
    [1, 2, 3, 4, 5],  # Resiliencia
    [5, 4, 3, 2, 1],  # Complejidad op. ↓
    [5, 3, 3, 2, 1]   # Madurez req. ↓
]

# --- ENCABEZADO ---
st.caption("EJERCICIO 6 · BIG DATA")
st.title("Evaluación comparativa de arquitecturas Big Data")
st.markdown("Matriz multicriterio · 5 alternativas arquitectónicas · 10 criterios ponderados · ranking ajustable")
st.divider()

# --- 1. ALTERNATIVAS ---
st.subheader("1. Alternativas arquitectónicas evaluadas")
cols = st.columns(5)

archs_info = [
    ("Local monolítico", "Scripts / notebooks + archivos CSV o JSON en disco local. Sin orquestación formal."),
    ("Pipeline Docker + columnar", "Docker Compose + Parquet / DuckDB + Airflow o Prefect. Almacenamiento orientado a columnas."),
    ("Microservicios contenerizados", "Kafka + Spark / Flink + MinIO o Postgres. Orquestado en Kubernetes."),
    ("Data Lake / Lakehouse", "S3 / ADLS + Delta Lake o Iceberg + Databricks / Spark + catálogo de metadatos."),
    ("Cloud / Híbrida", "BigQuery, Snowflake o Redshift + managed services + SLAs garantizados.")
]

for i, col in enumerate(cols):
    with col:
        st.markdown(f"**<span style='color:{COLORS[i]}'>{SHORT_NAMES[i]} — {archs_info[i][0]}</span>**", unsafe_allow_html=True)
        st.caption(archs_info[i][1])

st.divider()

# --- 2. PONDERACIONES (SLIDERS) ---
st.subheader("2. Criterios y ponderaciones")
st.caption("Ajusta los sliders para ver cómo cambia el ranking. Los pesos se normalizan automáticamente a 100%. Criterios con ↓ están invertidos (mayor ptje = mejor).")

# Crear sliders en columnas para no ocupar tanto espacio vertical
slider_cols = st.columns(2)
user_weights = []

for i, crit in enumerate(CRIT):
    col_idx = i % 2
    with slider_cols[col_idx]:
        w = st.slider(crit, min_value=1, max_value=30, value=INIT_W[i], step=1, key=f"w_{i}")
        user_weights.append(w)

# Normalizar pesos
total_weight = sum(user_weights)
norm_weights = [w / total_weight for w in user_weights]

# Calcular totales ponderados
totals = []
for j in range(5):
    t = sum(SCORES[i][j] * norm_weights[i] for i in range(10))
    totals.append(t)

st.divider()

# --- 3. JUSTIFICACIÓN ---
with st.expander("Ver Justificación de ponderaciones"):
    just_data = {
        "Criterio": CRIT,
        "Peso Base": [f"{w}%" for w in INIT_W],
        "Justificación": [
            "Latencia y throughput condicionan directamente los SLAs del sistema analítico.",
            "Restricción operativa dominante; determina la viabilidad inicial del proyecto.",
            "Criterio definitorio de Big Data; el crecimiento del volumen invalida arquitecturas inadecuadas.",
            "Costo oculto más subestimado: la deuda técnica acumulada destruye equipos en el mediano plazo.",
            "Fundamental para ciencia de datos, auditoría de modelos, y cumplimiento normativo.",
            "Relevancia creciente por GDPR, LGPD y regulaciones sectoriales.",
            "Riesgo reputacional y legal si se compromete confidencialidad.",
            "Continuidad de negocio; el MTTR ante fallos determina el impacto real.",
            "Inversamente proporcional a la productividad; el overhead limita la entrega de valor.",
            "Barrera real de adopción frecuentemente ignorada; arquitecturas brillantes fallan sin capacidades."
        ]
    }
    st.table(pd.DataFrame(just_data))

# --- 4. MATRIZ DE EVALUACIÓN ---
st.subheader("4. Matriz de evaluación (escala 1 – 5)")

# Preparar DataFrame para mostrar la matriz
matrix_dict = {
    "Criterio": CRIT + ["**Puntuación Total Ponderada**"],
    "Peso Normalizado": [f"{w*100:.1f}%" for w in norm_weights] + ["**100%**"]
}

for j in range(5):
    col_data = [SCORES[i][j] for i in range(10)] + [f"**{totals[j]:.2f}**"]
    matrix_dict[f"{NAMES[j]}"] = col_data

df_matrix = pd.DataFrame(matrix_dict)
st.markdown(df_matrix.to_html(escape=False, index=False), unsafe_allow_html=True)

st.divider()

# --- 5. RANKING MULTICRITERIO ---
st.subheader("5. Ranking multicriterio")
st.caption("Rango máximo teórico: 5.00")

# Ordenar totales para el gráfico
ranked_indices = sorted(range(len(totals)), key=lambda k: totals[k], reverse=True)
ranked_names = [NAMES[i] for i in ranked_indices]
ranked_totals = [totals[i] for i in ranked_indices]
ranked_colors = [COLORS[i] for i in ranked_indices]

# Gráfico de barras horizontales usando Plotly
fig_bar = go.Figure(go.Bar(
    x=ranked_totals,
    y=ranked_names,
    orientation='h',
    marker_color=ranked_colors,
    text=[f"{v:.2f}" for v in ranked_totals],
    textposition='inside'
))
fig_bar.update_layout(
    xaxis=dict(range=[0, 5.0]),
    margin=dict(l=0, r=0, t=20, b=0),
    height=300,
    yaxis={'categoryorder': 'total ascending'}
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# --- 6. RADAR ---
st.subheader("6. Perfil de fortalezas por arquitectura (puntuaciones brutas)")

fig_radar = go.Figure()

for j in range(5):
    # Cerrar el polígono repitiendo el primer valor
    r_values = [SCORES[i][j] for i in range(10)]
    r_values.append(r_values[0])
    theta_values = CRIT.copy()
    theta_values.append(CRIT[0])
    
    fig_radar.add_trace(go.Scatterpolar(
        r=r_values,
        theta=theta_values,
        fill='toself',
        name=NAMES[j],
        line_color=COLORS[j],
        opacity=0.7
    ))

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 5], tickangle=0)
    ),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    margin=dict(l=40, r=40, t=40, b=40),
    height=500
)
st.plotly_chart(fig_radar, use_container_width=True)

st.divider()

# --- 7. ESCENARIOS ---
st.subheader("7. Recomendación por escenario")
sc_cols = st.columns(4)

scenarios = [
    {"tag": "Equipo pequeño · recursos limitados", "rec": "B — Pipeline Docker + Columnar", "why": "Docker Compose + DuckDB/Parquet combina costo mínimo con reproducibilidad alta. Escala a decenas de millones de filas sin cambiar de stack."},
    {"tag": "Organización con crecimiento de volumen", "rec": "D — Data Lake / Lakehouse", "why": "Delta Lake o Apache Iceberg ofrecen transacciones ACID. Escalan de TB a PB sin re-arquitectura. Facilita la transición hacia gobernanza."},
    {"tag": "Organización regulada", "rec": "E — Cloud / Híbrida (D como respaldo)", "why": "Servicios gestionados con certificaciones SOC 2 / ISO 27001 y linaje de datos nativo. Snowflake o BigQuery reducen drásticamente el overhead de compliance."},
    {"tag": "Datos semiestructurados · eventos", "rec": "C — Microservicios", "why": "Kafka para ingesta de eventos, Flink/Spark para tiempo real. K8s permite escalar consumidores. Ideal para IoT y clickstreams."}
]

for i, col in enumerate(sc_cols):
    with col:
        st.info(f"**{scenarios[i]['tag']}**\n\n**{scenarios[i]['rec']}**\n\n{scenarios[i]['why']}")

st.divider()

# --- 8. TRADE-OFFS ---
st.subheader("8. Discusión de trade-offs y limitaciones")
to_cols = st.columns(3)

tradeoffs = [
    ("Sensibilidad a las ponderaciones", "Mover el criterio 'costo' en ±5 % invierte el ranking. No existe una arquitectura dominante universal; es contexto-dependiente."),
    ("Colapso de arquitecturas híbridas", "Asume arquitecturas puras. En la práctica, las organizaciones migran progresivamente. El ranking no captura rutas de migración."),
    ("Escala ordinal vs. cardinal", "Asumir linealidad entre 1→2 y 4→5 es una simplificación. Pasar de 4 a 5 en escalabilidad puede significar órdenes de magnitud."),
    ("Criterios ausentes", "Vendor lock-in, observabilidad, Feature Stores, latencia de ingesta y curva de adopción no están incluidos."),
    ("Costo: lista vs. TCO a 3 años", "La arquitectura E tiene mayor gasto mensual, pero reduce el headcount de ingeniería. El TCO a 36 meses puede invertir el ranking."),
    ("El equipo como variable crítica", "Una arquitectura óptima con un equipo sin experiencia es peor que una subóptima dominada. La madurez es la barrera real.")
]

for i, (title, text) in enumerate(tradeoffs):
    col_idx = i % 3
    with to_cols[col_idx]:
        st.success(f"**{title}**\n\n{text}")

st.markdown("\n> **Conclusión metodológica:** elegir una infraestructura de datos no es seleccionar la herramienta de moda — es resolver un problema de optimización multicriterio con restricciones reales: datos, carga, operación, presupuesto, riesgos regulatorios y capacidades efectivas del equipo. La matriz presentada es un punto de partida analítico, no un oráculo.")