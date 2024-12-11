# Simulación de un Sistema de Control de Tracción

Este programa permite simular un sistema de control de tracción de un automóvil de calle. Mediante distintos deslizadores en la pantalla, se podrá simular el acelerador del automóvil, y cambiar el agarre del asfalto para cada rueda. En tiempo real, el programa calculará la respuesta del vehículo a las condiciones dadas. Se mostrarán distintos gráficos con variables significativas, como las velocidades de las ruedas y otros parámetros.
Cuando se activa el sistema de control de tracción, este limita la velocidad de las ruedas que tienen poco agarre, aplicando los frenos. Esto reduce significativamente el bloqueo de los neumáticos (es decir, la reducción brusca en su velocidad) cuando recuperan la tracción.

## Variables Graficadas
- Velocidad de cada rueda.
- Aceleración de cada rueda.
- Agarre de cada rueda.
- Freno aplicado a cada rueda.
- Velocidad promedio de las otras ruedas (esto le dice al sistema de control de tracción la velocidad objetivo que tiene que mantener en cada una de ellas).
- Posición del acelerador.

Si el usuario así lo desea, puede ajustar las constantes en `simulacion.py`, para simular el comportamiento de un automóvil de diferentes prestaciones (por ejemplo, distinta velocidad máxima o aceleración). Además, se puede ajustar la sensibilidad del control de tracción, para definir qué tanto más rápido debe estar girando una rueda en comparación a las demás, para que se active dicho sistema. 

## Requisitos
- Python 3.x
- Bibliotecas: matplotlib, tkinter

## Instalación de Bibliotecas
Ejecute los siguientes comandos para instalar las bibliotecas necesarias:
```sh
pip install matplotlib
pip install tk
```

## Ejecución de la Simulación
1. Abra una terminal o línea de comandos.
2. Navegue al directorio donde se encuentra el archivo `simulacion.py`.
3. Ejecute el siguiente comando:
```sh
python simulacion.py
```