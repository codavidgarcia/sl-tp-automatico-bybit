# 🎨 Iconos para la Aplicación

Para crear ejecutables con iconos personalizados, necesitas los siguientes archivos:

## 📁 Archivos de Iconos Necesarios

### Windows
- **Archivo**: `icon.ico`
- **Formato**: ICO (Windows Icon)
- **Tamaños recomendados**: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256 píxeles
- **Herramientas**: 
  - Online: [favicon.io](https://favicon.io/favicon-converter/)
  - Software: GIMP, Photoshop, IcoFX

### macOS
- **Archivo**: `icon.icns`
- **Formato**: ICNS (Apple Icon Image)
- **Tamaños recomendados**: 16x16 hasta 1024x1024 píxeles
- **Herramientas**:
  - Online: [cloudconvert.com](https://cloudconvert.com/png-to-icns)
  - macOS: `iconutil` (comando nativo)
  - Software: Icon Composer (Xcode)

### Linux
- **Archivo**: `icon.png`
- **Formato**: PNG
- **Tamaño recomendado**: 256x256 píxeles
- **Transparencia**: Soportada

## 🎯 Crear Iconos desde una Imagen

### Paso 1: Preparar Imagen Base
- Formato: PNG con fondo transparente
- Tamaño: 512x512 píxeles (mínimo)
- Diseño: Simple, reconocible a tamaños pequeños

### Paso 2: Convertir a Formatos Específicos

#### Para Windows (.ico):
```bash
# Usando ImageMagick
convert icon.png -resize 256x256 icon.ico

# Online
# Sube tu PNG a favicon.io y descarga el ICO
```

#### Para macOS (.icns):
```bash
# Crear iconset
mkdir icon.iconset
sips -z 16 16 icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32 icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32 icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64 icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256 icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512 icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png

# Crear ICNS
iconutil -c icns icon.iconset
```

## 🚀 Sugerencias de Diseño

### Tema Trading/Finanzas
- 📈 Gráfico de líneas ascendente
- 💰 Símbolo de moneda
- 🎯 Diana/objetivo
- ⚡ Rayo (velocidad/automatización)
- 🔄 Flechas circulares (automatización)

### Colores Recomendados
- **Verde**: #27ae60 (ganancias, positivo)
- **Azul**: #3498db (confianza, tecnología)
- **Dorado**: #f39c12 (premium, valor)
- **Blanco/Negro**: Contraste y legibilidad

## 🛠️ Herramientas Recomendadas

### Gratuitas
- **GIMP**: Editor completo
- **Canva**: Plantillas prediseñadas
- **Figma**: Diseño vectorial
- **favicon.io**: Conversión online

### De Pago
- **Adobe Illustrator**: Diseño vectorial profesional
- **Adobe Photoshop**: Edición de imágenes
- **Sketch** (macOS): Diseño de interfaces

## 📝 Notas Importantes

1. **Sin iconos**: La aplicación funcionará sin iconos, pero usará el icono por defecto del sistema
2. **Tamaño del ejecutable**: Los iconos agregan ~50KB al ejecutable
3. **Calidad**: Usa imágenes vectoriales cuando sea posible para mejor escalado
4. **Licencias**: Asegúrate de tener derechos sobre las imágenes que uses

## 🎨 Ejemplo de Icono Simple

Si quieres crear un icono básico rápidamente:

1. Crea un cuadrado de 512x512 píxeles
2. Fondo transparente
3. Dibuja un gráfico simple ascendente en verde
4. Agrega el texto "SL/TP" en la parte inferior
5. Convierte a los formatos necesarios

¡Una vez que tengas los archivos de iconos, los scripts de construcción los detectarán automáticamente!
