import time
import math
import concurrent.futures
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 1. Tarea Computacional (Simulación de procesamiento pesado)
# ---------------------------------------------------------
def computacion_pesada(x):
    """Simula una agregación compleja o cálculo de indicadores."""
    resultado = 0
    # Un ciclo para añadir peso computacional artificial
    for i in range(50):
        resultado += math.sin(x) * math.cos(x + i)
    return resultado

def procesar_chunk(chunk):
    """Procesa un lote de datos de forma secuencial."""
    return [computacion_pesada(x) for x in chunk]

if __name__ == '__main__':
    # 2. Generación del Dataset (1.000.000 de registros)
    N = 1_000_000
    print(f"Generando dataset de {N} registros...")
    data = list(range(N))
    
    tiempos = {}
    
    # 3. Ejecución Secuencial
    print("\n--- Ejecución Secuencial ---")
    start = time.time()
    # Ejecutamos todo en el proceso principal
    resultado_seq = procesar_chunk(data)
    t1 = time.time() - start
    tiempos[1] = t1
    print(f"Tiempo secuencial (1 proceso): {t1:.4f} segundos")

    # 4. Ejecución Paralela
    print("\n--- Ejecución Paralela ---")
    procesos_a_probar = [2, 4, 8]
    
    for p in procesos_a_probar:
        start = time.time()
        
        # Particionamiento: Dividir datos en 'p' chunks
        chunk_size = math.ceil(N / p)
        chunks = [data[i:i + chunk_size] for i in range(0, N, chunk_size)]
        
        # Ejecución multiproceso
        with concurrent.futures.ProcessPoolExecutor(max_workers=p) as executor:
            # Mapeamos la función procesar_chunk a cada lote
            resultados_par = list(executor.map(procesar_chunk, chunks))
            
        tp = time.time() - start
        tiempos[p] = tp
        
        # Cálculos de métricas
        sp = t1 / tp          # Speedup
        ep = sp / p           # Eficiencia
        
        print(f"Procesos: {p} | Tiempo: {tp:.4f}s | Speedup: {sp:.2f}x | Eficiencia: {ep:.2f}")

    # 5. Generación del Gráfico
    procesos = list(tiempos.keys())
    speedups = [tiempos[1] / tiempos[p] for p in procesos]
    eficiencias = [speedups[i] / procesos[i] for i in range(len(procesos))]

    plt.figure(figsize=(10, 5))

    # Gráfico de Speedup
    plt.subplot(1, 2, 1)
    plt.plot(procesos, speedups, marker='o', label='Speedup Real')
    plt.plot(procesos, procesos, linestyle='--', color='gray', label='Speedup Ideal (Lineal)')
    plt.xlabel('Número de Procesos (p)')
    plt.ylabel('Speedup (Sp)')
    plt.title('Speedup vs Número de Procesos')
    plt.grid(True)
    plt.legend()

    # Gráfico de Eficiencia
    plt.subplot(1, 2, 2)
    plt.plot(procesos, eficiencias, marker='o', color='green')
    plt.axhline(y=1, linestyle='--', color='gray', label='Eficiencia Ideal (1.0)')
    plt.xlabel('Número de Procesos (p)')
    plt.ylabel('Eficiencia (Ep)')
    plt.title('Eficiencia vs Número de Procesos')
    plt.grid(True)
    plt.ylim(0, 1.1)
    plt.legend()

    plt.tight_layout()
    plt.show()