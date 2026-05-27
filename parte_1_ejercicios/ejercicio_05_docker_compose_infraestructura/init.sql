-- =============================================================
--  init.sql — Inicialización de la base de datos dsdb
--  Ejecutado automáticamente por el contenedor PostgreSQL
--  la primera vez que se crea el volumen.
-- =============================================================

-- Esquema dedicado al proyecto
CREATE SCHEMA IF NOT EXISTS ventas;

-- ------------------------------------------------------------------
-- Tabla de productos
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventas.productos (
    id               SERIAL PRIMARY KEY,
    nombre           VARCHAR(120)   NOT NULL,
    categoria        VARCHAR(60)    NOT NULL,
    precio_unitario  NUMERIC(10, 2) NOT NULL CHECK (precio_unitario > 0),
    creado_en        TIMESTAMP      DEFAULT NOW()
);

-- ------------------------------------------------------------------
-- Tabla de transacciones de venta
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventas.transacciones (
    id           SERIAL PRIMARY KEY,
    producto_id  INTEGER        NOT NULL REFERENCES ventas.productos(id),
    cantidad     SMALLINT       NOT NULL CHECK (cantidad > 0),
    fecha        DATE           NOT NULL,
    region       VARCHAR(60)    NOT NULL,
    canal        VARCHAR(30)    NOT NULL,   -- 'online' | 'tienda' | 'b2b'
    total        NUMERIC(12, 2) NOT NULL,
    registrado_en TIMESTAMP     DEFAULT NOW()
);

-- ------------------------------------------------------------------
-- Índices para acelerar consultas frecuentes
-- ------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_trans_fecha
    ON ventas.transacciones(fecha);

CREATE INDEX IF NOT EXISTS idx_trans_producto
    ON ventas.transacciones(producto_id);

CREATE INDEX IF NOT EXISTS idx_trans_region
    ON ventas.transacciones(region);

-- ------------------------------------------------------------------
-- Vista para reportes rápidos
-- ------------------------------------------------------------------
CREATE OR REPLACE VIEW ventas.reporte_diario AS
SELECT
    t.fecha,
    p.categoria,
    t.region,
    t.canal,
    COUNT(*)                        AS num_ventas,
    SUM(t.cantidad)                 AS unidades_vendidas,
    ROUND(SUM(t.total)::NUMERIC, 2) AS ingresos_totales,
    ROUND(AVG(t.total)::NUMERIC, 2) AS ticket_promedio
FROM ventas.transacciones t
JOIN ventas.productos p ON p.id = t.producto_id
GROUP BY t.fecha, p.categoria, t.region, t.canal;

-- Mensaje de confirmación visible en los logs del contenedor
DO $$ BEGIN
    RAISE NOTICE 'Base de datos dsdb inicializada correctamente.';
END $$;
