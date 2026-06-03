# Ejercicio 3 — Paralelismo Local: Speedup y Eficiencia

Benchmark experimental de paralelismo CPU usando Python multiproceso. El objetivo es medir cómo se comporta el tiempo de ejecución al distribuir una tarea de cómputo intensivo entre varios procesos, y contrastar los resultados con los modelos teóricos de Speedup ideal y Ley de Amdahl.

---

## ¿Qué hace el programa?

Toma un dataset de 1.000.000 de números y aplica sobre cada uno una operación matemática pesada (suma de seno y coseno en 50 iteraciones). Primero lo ejecuta de forma secuencial para tener una línea base, y luego lo reparte entre 2, 4, 8... procesos (según los cores disponibles en la máquina) usando `ProcessPoolExecutor`.

Con los tiempos medidos calcula:
- **Speedup**: cuánto más rápido es la versión paralela respecto a la secuencial
- **Eficiencia**: qué fracción del speedup ideal se está aprovechando realmente
- **Ley de Amdahl**: estima la fracción serial del programa ajustando la curva teórica a los datos reales con `scipy.optimize.curve_fit`

Al final genera un gráfico con los tres análisis y lo guarda como PNG.

---

## Decisiones de diseño

**Por qué `ProcessPoolExecutor` y no `ThreadPoolExecutor`**  
Python tiene el GIL (Global Interpreter Lock), que impide que dos hilos ejecuten código Python puro al mismo tiempo. Para tareas CPU-bound como esta, los hilos no ayudan. Los procesos sí, porque cada uno tiene su propio intérprete.

**Por qué se pre-computan los chunks antes de medir**  
Dividir la lista en trozos es trabajo de Python puro que no forma parte del cómputo paralelo. Si se incluye dentro del cronómetro, el Speedup aparece artificialmente más bajo. La partición se hace una sola vez antes de cualquier medición.

**Por qué se repite cada medición 3 veces y se toma la mediana**  
Una sola medición puede estar inflada por el scheduler del SO, una interrupción de hardware, o el arranque inicial del pool de procesos. Con 3 repeticiones y mediana se reduce ese ruido sin que el benchmark tarde demasiado.

**Por qué hay un warm-up**  
La primera vez que se lanza `ProcessPoolExecutor`, el sistema operativo tiene que hacer el fork de los procesos desde cero. Eso tarda más que las ejecuciones siguientes. El warm-up descarta esa primera corrida para que no contamine la medición.

**Por qué el gráfico de eficiencia excluye p=1**  
Por definición, E(1) = S(1)/1 = 1.0 siempre. Incluirlo no aporta información y comprime el eje Y, haciendo que la degradación real al escalar se vea menos clara.

---

## Requisitos

```
Python >= 3.9
matplotlib
numpy
scipy
```

Instalar dependencias:

```bash
pip install matplotlib numpy scipy
```

---

## Cómo ejecutar

```bash
cd ejercicio_03_paralelismo_local
python programa.py
```

El programa detecta automáticamente el número de CPUs lógicas de la máquina y ajusta las configuraciones a probar. No hace falta modificar nada.

Al terminar imprime en consola los tiempos, Speedup, Eficiencia y el resultado del análisis de Amdahl, y guarda el gráfico en `speedup_eficiencia_amdahl.png`.

---

## Ejemplo de salida

```
=================================================================
  BENCHMARK DE PARALELISMO — Contexto de hardware
=================================================================
  SO              : Windows 11
  CPUs lógicas    : 8
  Dataset         : 1,000,000 registros
  Repeticiones    : 3 por configuración (se reporta mediana)
  Configs paralelo: [2, 4, 8]
=================================================================

  EJECUCIÓN SECUENCIAL (p = 1)
  Run 1: 18.3241s
  Run 2: 18.2987s
  Run 3: 18.3104s
  → Mediana T1 = 18.3104s

  p= 2 | [r1:9.812s  r2:9.798s  r3:9.804s]
        Mediana Tp=9.804s | Speedup=1.868x | Eficiencia=0.934

  p= 4 | [r1:5.201s  r2:5.188s  r3:5.195s]
        Mediana Tp=5.195s | Speedup=3.524x | Eficiencia=0.881

  p= 8 | [r1:3.142s  r2:3.137s  r3:3.149s]
        Mediana Tp=3.137s | Speedup=5.839x | Eficiencia=0.730

  ANÁLISIS — LEY DE AMDAHL
  Fracción serial estimada (f) : 0.0312  (3.12%)
  Fracción paralela (1-f)      : 0.9688  (96.88%)
  Speedup máximo teórico (1/f) : 32.05x
  Bondad de ajuste R²          : 0.9981
  → Tarea altamente paralelizable. El overhead serial es mínimo.
```

---

## Estructura del análisis

```
programa.py
│
├── computacion_pesada()     ← carga CPU-bound pura (sin I/O)
├── procesar_chunk()         ← procesa un lote completo
│
├── medir_secuencial()       ← cronometro con perf_counter
├── medir_paralelo()         ← solo mide el cómputo, no el chunking
│
├── speedup_amdahl()         ← modelo teórico S(p) = 1/(f + (1-f)/p)
├── estimar_fraccion_serial() ← ajuste de curva con scipy
│
└── main
    ├── 0. Contexto de hardware
    ├── 1. Generación del dataset
    ├── 2. Pre-cómputo de chunks (fuera del timer)
    ├── 3. Warm-up
    ├── 4. Medición secuencial (3 runs → mediana)
    ├── 5. Medición paralela (3 runs por config → mediana)
    ├── 6. Análisis de Ley de Amdahl
    └── 7. Generación de gráficos (3 paneles → PNG)
```

---

## Interpretación de resultados

El Speedup real siempre queda por debajo del ideal lineal. Eso es normal y esperado: siempre hay una fracción del programa que no se puede paralelizar (inicialización, serialización de datos entre procesos, recolección de resultados). La Ley de Amdahl cuantifica exactamente esa fracción y permite predecir cuál sería el Speedup máximo alcanzable aunque se tuvieran infinitos procesadores.

Si la eficiencia baja mucho al pasar de 4 a 8 procesos, puede indicar que la máquina tiene 4 cores físicos y los 4 adicionales son hilos lógicos (hyperthreading), que no ayudan en tareas puramente CPU-bound.
