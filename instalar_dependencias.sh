#!/bin/bash

# Script para instalar dependencias del proyecto
# Incluye manejo de entorno virtual para evitar conflictos

echo "================================================"
echo "Instalador de Dependencias - Contabilidad IConstruye"
echo "================================================"
echo ""

# Detectar si existe un entorno virtual
if [ -d "venv" ]; then
    echo "✓ Entorno virtual encontrado en ./venv"
    ACTIVATE_SCRIPT="venv/bin/activate"
else
    echo "⚠️  No se encontró entorno virtual"
    echo "¿Deseas crear uno? (y/n)"
    read -r respuesta

    if [ "$respuesta" = "y" ] || [ "$respuesta" = "Y" ]; then
        echo "📦 Creando entorno virtual..."
        python3 -m venv venv
        ACTIVATE_SCRIPT="venv/bin/activate"
        echo "✓ Entorno virtual creado"
    else
        echo "⚠️  Instalando sin entorno virtual (puede requerir permisos)"
        ACTIVATE_SCRIPT=""
    fi
fi

# Activar entorno virtual si existe
if [ -n "$ACTIVATE_SCRIPT" ]; then
    echo "🔄 Activando entorno virtual..."
    source "$ACTIVATE_SCRIPT"
fi

# Actualizar pip
echo ""
echo "📦 Actualizando pip..."
python3 -m pip install --upgrade pip

# Instalar dependencias desde requirements.txt
echo ""
echo "📦 Instalando dependencias desde requirements.txt..."
python3 -m pip install -r requirements.txt

# Verificar instalación de pdfplumber específicamente
echo ""
echo "🔍 Verificando instalación de pdfplumber..."
if python3 -c "import pdfplumber" 2>/dev/null; then
    echo "✓ pdfplumber instalado correctamente"
else
    echo "❌ Error: pdfplumber no se instaló correctamente"
    exit 1
fi

# Verificar otras dependencias críticas
echo ""
echo "🔍 Verificando otras dependencias críticas..."

declare -a DEPS=("yaml" "selenium" "pandas" "openpyxl" "requests" "googleapiclient")
MISSING=0

for dep in "${DEPS[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo "  ✓ $dep"
    else
        echo "  ❌ $dep - NO INSTALADO"
        MISSING=$((MISSING + 1))
    fi
done

echo ""
if [ $MISSING -eq 0 ]; then
    echo "================================================"
    echo "✅ Todas las dependencias instaladas correctamente"
    echo "================================================"
    echo ""
    echo "Para activar el entorno virtual en el futuro:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Para ejecutar el script de prueba de PDFs:"
    echo "  python test_pdf_extractor.py"
    echo ""
else
    echo "================================================"
    echo "⚠️  $MISSING dependencia(s) faltante(s)"
    echo "Revisa los errores arriba e intenta instalarlas manualmente"
    echo "================================================"
    exit 1
fi
