import math
import os
import platform
import concurrent.futures
import time
from statistics import median

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

N = 1_000_000
REPETICIONES = 3

N_CPUS = os.cpu_count() or 4
_par = sorted({p for p in [2, 4, 8, 16, 32] if p <= N_CPUS})
if not _par:
    _par = [min(2, N_CPUS)]
PROCESOS_PARALELOS = _par

def computacion_pesada(x: float) -> float:
    resultado = 0.0
    for i in range(50):
        resultado += math.sin(x) * math.cos(x + i)
    return resultado

def procesar_chunk(chunk: list) -> list:
    return [computacion_pesada(x) for x in chunk]

def medir_secuencial(data: list) -> float:
    t0 = time.perf_counter()
    procesar_chunk(data)
    return time.perf_counter() - t0

def medir_paralelo(chunks: list, p: int) -> float:
    t0 = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=p) as executor:
        list(executor.map(procesar_chunk, chunks))
    return time.perf_counter() - t0

def speedup_amdahl(p: np.ndarray, f: float) -> np.ndarray:
    return 1.0 / (f + (1.0 - f) / p)

def estimar_fraccion_serial(ps: list, speedups: list) -> tuple:
    p_arr = np.array(ps, dtype=float)
    s_arr = np.array(speedups, dtype=float)

    try:
        popt, _ = curve_fit(
            speedup_amdahl,
            p_arr,
            s_arr,
            p0=[0.1],
            bounds=(0.0, 1.0),
            maxfev=5000,
        )
        f_est = float(popt[0])

        s_pred = speedup_amdahl(p_arr, f_est)
        ss_res = np.sum((s_arr - s_pred) ** 2)
        ss_tot = np.sum((s_arr - np.mean(s_arr)) ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

        return f_est, r2
    except Exception:
        return float("nan"), float("nan")

if __name__ == "__main__":

    print("=" * 65)
    print("  BENCHMARK DE PARALELISMO — Contexto de hardware")
    print("=" * 65)
    print(f"  SO              : {platform.system()} {platform.release()}")
    print(f"  Procesador      : {platform.processor() or 'N/D'}")
    print(f"  CPUs lógicas    : {N_CPUS}")
    print(f"  Python          : {platform.python_version()}")
    print(f"  Dataset         : {N:,} registros")
    print(f"  Repeticiones    : {REPETICIONES} por configuración (se reporta mediana)")
    print(f"  Configs paralelo: {PROCESOS_PARALELOS}")
    print("=" * 65)

    print(f"\nGenerando dataset de {N:,} registros...")
    data = list(range(N))

    print("\nPre-computando particiones de datos (fuera del timer)...")
    chunks_por_p = {}
    for p in PROCESOS_PARALELOS:
        chunk_size = math.ceil(N / p)
        chunks_por_p[p] = [data[i:i + chunk_size] for i in range(0, N, chunk_size)]
    print("  Particiones listas.\n")

    print("Warm-up (ejecución descartada, sobre muestra reducida)...")
    _ = medir_secuencial(data[:10_000])
    if PROCESOS_PARALELOS:
        p_wu = PROCESOS_PARALELOS[0]
        sz_wu = math.ceil(10_000 / p_wu)
        chunks_wu = [data[i:i + sz_wu] for i in range(0, 10_000, sz_wu)]
        _ = medir_paralelo(chunks_wu, p_wu)
    print("  Warm-up completado.\n")

    print("─" * 65)
    print("  EJECUCIÓN SECUENCIAL (p = 1)")
    print("─" * 65)

    tiempos_seq = []
    for r in range(REPETICIONES):
        t = medir_secuencial(data)
        tiempos_seq.append(t)
        print(f"  Run {r + 1}: {t:.4f}s")

    T1 = median(tiempos_seq)
    print(f"  → Mediana T1 = {T1:.4f}s\n")

    print("─" * 65)
    print("  EJECUCIÓN PARALELA")
    print("─" * 65)

    tiempos_medianas = {1: T1}

    for p in PROCESOS_PARALELOS:
        tiempos_runs = []
        for r in range(REPETICIONES):
            t = medir_paralelo(chunks_por_p[p], p)
            tiempos_runs.append(t)

        Tp = median(tiempos_runs)
        tiempos_medianas[p] = Tp

        Sp = T1 / Tp
        Ep = Sp / p

        detalle = "  ".join(f"r{i+1}:{v:.3f}s" for i, v in enumerate(tiempos_runs))
        print(f"\n  p={p:2d} | [{detalle}]")
        print(f"        Mediana Tp={Tp:.4f}s | Speedup={Sp:.3f}x | Eficiencia={Ep:.3f}")

    print("\n" + "─" * 65)
    print("  ANÁLISIS — LEY DE AMDAHL")
    print("─" * 65)

    ps_fit       = PROCESOS_PARALELOS
    speedups_fit = [T1 / tiempos_medianas[p] for p in ps_fit]

    f_est, r2 = estimar_fraccion_serial(ps_fit, speedups_fit)

    if not math.isnan(f_est):
        s_max_teo = 1.0 / f_est if f_est > 0 else float("inf")
        print(f"  Fracción serial estimada (f) : {f_est:.4f}  ({f_est * 100:.2f}%)")
        print(f"  Fracción paralela (1-f)      : {1 - f_est:.4f}  ({(1 - f_est) * 100:.2f}%)")
        print(f"  Speedup máximo teórico (1/f) : {s_max_teo:.2f}x")
        print(f"  Bondad de ajuste R²          : {r2:.4f}")
        print()
        if f_est < 0.05:
            print("  → Tarea altamente paralelizable. El overhead serial es mínimo.")
        elif f_est < 0.20:
            print("  → Fracción serial moderada. Ganancias reales pero por debajo del ideal.")
        else:
            print("  → Fracción serial significativa. El Speedup se satura rápidamente.")
        sp_ncpus = speedup_amdahl(N_CPUS, f_est)
        print(f"  → Con {N_CPUS} CPUs lógicas, el modelo predice Speedup = {sp_ncpus:.2f}x (teórico).")
    else:
        print("  No se pudo ajustar la curva de Amdahl (datos insuficientes).")

    todos_ps  = [1] + PROCESOS_PARALELOS
    todos_sp  = [T1 / tiempos_medianas[p] for p in todos_ps]

    ps_ef  = PROCESOS_PARALELOS
    eps_ef = [T1 / tiempos_medianas[p] / p for p in ps_ef]

    p_range = np.linspace(1, max(todos_ps) * 1.15, 400)
    sp_amdahl_curve = (speedup_amdahl(p_range, f_est)
                       if not math.isnan(f_est) else None)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(
        f"Paralelismo Local — {N:,} registros · {REPETICIONES} repeticiones · mediana\n"
        f"Hardware: {N_CPUS} CPUs lógicas · {platform.system()} {platform.release()}",
        fontsize=11, fontweight="bold"
    )

    ax1 = axes[0]
    ax1.plot(todos_ps, todos_sp, marker='o', linewidth=2,
             color='steelblue', label='Speedup real (mediana)')
    ax1.plot(todos_ps, todos_ps, linestyle='--', color='gray',
             label='Speedup ideal (lineal)')
    if sp_amdahl_curve is not None:
        ax1.plot(p_range, sp_amdahl_curve, linestyle=':', color='tomato',
                 linewidth=2, label=f'Amdahl (f={f_est:.3f}, R²={r2:.3f})')
    ax1.set_xlabel('Número de procesos (p)')
    ax1.set_ylabel('Speedup  Sp = T₁ / Tp')
    ax1.set_title('Speedup vs Procesos')
    ax1.grid(True, alpha=0.4)
    ax1.legend(fontsize=8)

    ax2 = axes[1]
    ax2.plot(ps_ef, eps_ef, marker='s', linewidth=2,
             color='seagreen', label='Eficiencia real')
    ax2.axhline(y=1.0, linestyle='--', color='gray', label='Eficiencia ideal (1.0)')
    ax2.set_xlabel('Número de procesos (p)')
    ax2.set_ylabel('Eficiencia  Ep = Sp / p')
    ax2.set_title('Eficiencia vs Procesos\n(excluye p=1: E=1.0 por definición)')
    ax2.set_ylim(0, 1.15)
    ax2.grid(True, alpha=0.4)
    ax2.legend(fontsize=8)

    ax3 = axes[2]
    if sp_amdahl_curve is not None:
        ax3.plot(p_range, sp_amdahl_curve, linestyle='-', color='tomato',
                 linewidth=2, label=f'Modelo Amdahl (f={f_est:.3f})')
        ax3.plot(p_range, p_range, linestyle='--', color='gray',
                 label='Ideal (lineal)')
        ax3.scatter(todos_ps[1:], todos_sp[1:], color='steelblue',
                    zorder=5, label='Mediciones reales')
        s_max = 1.0 / f_est if f_est > 0 else None
        if s_max and s_max < 60:
            ax3.axhline(y=s_max, linestyle=':', color='tomato', alpha=0.6,
                        label=f'S_max = 1/f = {s_max:.1f}x')
        ax3.set_xlabel('Número de procesos (p)')
        ax3.set_ylabel('Speedup teórico')
        ax3.set_title(f'Ley de Amdahl\nFracción serial estimada: {f_est * 100:.1f}%')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.4)
    else:
        ax3.text(0.5, 0.5, "Datos insuficientes\npara el ajuste",
                 ha='center', va='center', transform=ax3.transAxes)
        ax3.set_title('Ley de Amdahl')

    plt.tight_layout()
    plt.savefig("speedup_eficiencia_amdahl.png", dpi=150, bbox_inches='tight')
    print("\nGráfico guardado: speedup_eficiencia_amdahl.png")
    plt.show()
