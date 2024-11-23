import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import defaultdict
from abc import ABC, abstractmethod
from typing import Dict, Mapping
import random
import tkinter as tk
import time
import threading

class Variable(ABC):
    """
    Representa una variable cuyo valor evoluciona en el tiempo.
    """
    def __init__(self, cota_inferior: float, cota_superior: float):
        self.cota_superior = cota_superior
        self.cota_inferior = cota_inferior

    @abstractmethod
    def valor(self) -> float:
        """
        Debe devolver el valor actualizado de la variable que representa.
        """
        pass

    def mas(self, otra: 'Variable') -> 'Variable':
        return Suma(self, otra)

    def menos(self, otra: 'Variable') -> 'Variable':
        return Suma(self, otra.por(Constante(-1)))

    def por(self, escalar: 'Variable') -> 'Variable':
        return Multiplicacion(self, escalar)
    
    def retardado(self, retardo_en_segundos: float) -> 'Variable':
        return VariableRetardada(self, retardo_en_segundos)
    
    def acotado(self, cota_inferior: 'Variable', cota_superior: 'Variable') -> 'Variable':
        return VariableAcotada(self, cota_inferior, cota_superior)

class Timer(ABC):
    TICK = 0.01 # segundos
    """
    Ejecuta un método cada cierto intervalo de tiempo, en un hilo separado.
    """
    def __init__(self):
        self._iniciar()

    @abstractmethod
    def tick(self):
        """
        Método que se quiere ejecutar en cada tick.
        """
        pass

    def _hacer_ticks(self):
        while True:
            self.tick()
            time.sleep(self.TICK)
        
    def _iniciar(self):
        """
        Inicia el temporizador en un hilo separado.
        """
        threading.Thread(target=self._hacer_ticks, daemon=True).start()

def tiempo_transcurrido_desde(t):
    return time.time() - t

class Graficos:
    """
    Grafica la evolución temporal de una cantidad arbitraria de variables.
    """
    def __init__(self, titulo: str = "Evolución Temporal de Variables", 
                 x_label: str = "Tiempo", y_label: str = "Valor", 
                 x_lim: int = 100, ventana_temporal: int = 10, 
                 graficos: Dict[str, Variable] = {}):
        """
        Inicializa el gráfico con múltiples subplots y configura las fuentes de datos directamente.
        """
        etiquetas = list(graficos.keys())
        if len(etiquetas) != len(set(etiquetas)):
            raise ValueError("No puede haber dos gráficos con la misma etiqueta.")

        self.fuentes = graficos
        self.variables = list(self.fuentes.keys())
        self.x_data = []
        self.y_data = defaultdict(list)
        self.x_lim = x_lim
        self.ventana_temporal = ventana_temporal
        self.frame = 0

        total_graficos = len(self.variables)
        filas = columnas = int(total_graficos**0.5) + 1

        self.fig, self.axes = plt.subplots(filas, columnas, figsize=(12, 12))
        self.axes = self.axes.flatten()

        for i in range(total_graficos, len(self.axes)):
            self.axes[i].axis('off')

        self.lines = {}
        for i, (ax, variable) in enumerate(zip(self.axes[:total_graficos], self.variables)):
            ax.set_xlim(0, self.x_lim)
            superior_y_lim = self.fuentes[variable].cota_superior
            inferior_y_lim = self.fuentes[variable].cota_inferior
            ax.set_ylim(inferior_y_lim, superior_y_lim)
            ax.set_title(variable)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_xticklabels([])  # Remove numerical indicators from X-axis
            line, = ax.plot([], [], lw=2)
            self.lines[variable] = line
            ax.legend().remove()

        self.fig.suptitle(f"{titulo} (últimos {ventana_temporal} segundos)")
        plt.subplots_adjust(hspace=0.5, wspace=0.5)

    def agregar_graficos_multiples(self, grupos_de_variables):
        """
        Agrupa en los mismos ejes cartesianos las variables pasadas por parámetro.
        :param grupos_de_variables: Lista de tuplas (tituloGrafico, [(etiqueta, variable)]).
        """
        colores = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'cyan', 'magenta']
        for ax, (titulo, grupo) in zip(self.axes, grupos_de_variables):
            if not grupo:
                continue
            ax.set_xlim(0, self.x_lim)
            ax.set_ylim(min(var.cota_inferior for _, var in grupo), 
                        max(var.cota_superior for _, var in grupo))
            for i, (etiqueta, variable) in enumerate(grupo):
                nombre_variable = f"{titulo} - {etiqueta}"
                self.fuentes[nombre_variable] = variable
                line, = ax.plot([], [], lw=2, label=etiqueta, color=colores[i % len(colores)])
                self.lines[nombre_variable] = line
            ax.legend()
            ax.set_title(titulo)
            ax.set_xlabel("Tiempo")
            ax.set_ylabel("Valor")
            ax.set_xticklabels([])  # Remove numerical indicators from X-axis
        plt.subplots_adjust(hspace=0.5, wspace=0.5)

    def actualizar_datos(self) -> None:
        """
        Actualiza los datos del gráfico con los valores más recientes de las fuentes.
        """
        datos = {var: fuente.valor() for var, fuente in self.fuentes.items()}
        self.agregar_datos(datos)

    def agregar_datos(self, datos: Dict[str, float]) -> None:
        self.x_data.append(self.frame)
        for variable, valor in datos.items():
            self.y_data[variable].append(valor)
        self.frame += 1

        if len(self.x_data) > self.ventana_temporal / 0.1:
            self.x_data = self.x_data[-int(self.ventana_temporal / 0.1):]
            for variable in self.y_data:
                self.y_data[variable] = self.y_data[variable][-int(self.ventana_temporal / 0.1):]

    def actualizar(self, _):
        for variable, line in self.lines.items():
            line.set_data(self.x_data, self.y_data[variable])
            if self.frame > self.x_lim:
                line.axes.set_xlim(self.frame - self.x_lim, self.frame)
        return self.lines.values()

    def iniciar(self, interval: int = 100) -> None:
        """
        Inicia la animación del gráfico.
        :param interval: Tiempo en milisegundos entre cada actualización.
        """
        def actualizar_y_graficar(_):
            self.actualizar_datos()
            return self.actualizar(_)
        # Si no me guardo ani en una variable, no funcionan los gráficos. Debe ser por algún tipo de recolección de basura.
        ani = animation.FuncAnimation(self.fig, actualizar_y_graficar, interval=interval, blit=True)
        plt.show()

class Deslizador():
    def __init__(self, etiqueta: str, minimo: float, maximo: float, inicial: float):
        self.etiqueta = etiqueta
        self.estado = inicial
        self.valor_minimo = minimo
        self.valor_maximo = maximo
        self._iniciar_en_hilo_paralelo()

    def valor_actual(self) -> float:
        return self.estado

    def _iniciar_en_hilo_paralelo(self):
        # Crear ventana de control con el deslizador
        threading.Thread(target=self._iniciar, daemon=True).start()

    def _iniciar(self):
        """
        Crea una ventana de Tkinter con un deslizador para controlar el estado de la fuente.
        """
        def on_slider_change(value):
            """ Cambiar el estado de la fuente según el valor del deslizador. """
            self.estado = float(value)

        # Crear la ventana de Tkinter
        root = tk.Tk()
        root.title(self.etiqueta)

        # Configurar el deslizador
        slider = tk.Scale(root, from_=self.valor_minimo, to=self.valor_maximo, resolution=0.01, orient=tk.HORIZONTAL, label=self.etiqueta, command=on_slider_change)
        slider.set(self.estado)  # Set initial state
        slider.pack(padx=20, pady=20)

        # Ejecutar la ventana de Tkinter en un hilo separado
        root.mainloop()

class Constante(Variable):
    def __init__(self, valor: float):
        self._valor = valor
        super().__init__(valor, valor)

    def valor(self) -> float:
        return self._valor

class VariableDeslizadorEnPantalla(Variable):
    def __init__(self, deslizador: Deslizador):
        self.deslizador = deslizador
        super().__init__(0, deslizador.valor_maximo)

    def valor(self) -> float:
        return self.deslizador.valor_actual()

class VariableAleatoriaUniforme(Variable):
    def __init__(self, cota_inferior: float, cota_superior: float):
        super().__init__(cota_inferior, cota_superior)

    def valor(self) -> float:
        return random.uniform(self.cota_inferior, self.cota_superior)

class VariableAleatoriaNormal(Variable):
    def __init__(self, media: float, desviacion_estandar: float):
        self.media = media
        self.desviacion_estandar = desviacion_estandar
        super().__init__(media - 3 * desviacion_estandar, media + 3 * desviacion_estandar)

    def valor(self) -> float:
        valor = random.gauss(self.media, self.desviacion_estandar)
        return max(self.cota_inferior, min(valor, self.cota_superior))

class VariableRetardada(Variable, Timer):
    def __init__(self, fuente: Variable, retardo_en_segundos: float):
        self.fuente = fuente
        self.retardo = retardo_en_segundos
        self.valores_pasados_de_la_fuente = []
        super().__init__(fuente.cota_inferior, fuente.cota_superior)
        Timer.__init__(self)

    def tick(self):
        self.valores_pasados_de_la_fuente.append((time.time(), self.fuente.valor()))
        # remuevo de la lista los valores pasados
        self.valores_pasados_de_la_fuente = [
            (t, v) for t, v in self.valores_pasados_de_la_fuente # solo deja los valores de la fuente
            if tiempo_transcurrido_desde(t) <= self.retardo # que hayan ocurrido hace un tiempo menor al tiempo de retardo #TODO: NO SÉ POR QUÉ FUNCIONA ESTO. NO SÉ EN QUÉ MOMENTO ESTÁ IMPLEMENTANDO EL DELAY, ESTO ERA SOLAMENTE PARA ELIMINAR LOS VALORES PASADOS.
        ]

    def valor(self) -> float:
        return self.valores_pasados_de_la_fuente[0][1] if self.valores_pasados_de_la_fuente else 0.0

class Suma(Variable):
    def __init__(self, var1: Variable, var2: Variable):
        self.var1 = var1
        self.var2 = var2
        super().__init__(var1.cota_inferior + var2.cota_inferior, var1.cota_superior + var2.cota_superior)

    def valor(self) -> float:
        return self.var1.valor() + self.var2.valor()

class Multiplicacion(Variable):
    def __init__(self, var: Variable, escalar: Variable):
        self.var = var
        self.escalar = escalar
        cota_superior = max(var.cota_superior * escalar.valor(), var.cota_inferior * escalar.valor())
        cota_inferior = min(var.cota_superior * escalar.valor(), var.cota_inferior * escalar.valor())
        super().__init__(cota_inferior, cota_superior)

    def valor(self) -> float:
        return self.var.valor() * self.escalar.valor()
    
class VariableAcotada(Variable):
    def __init__(self, var: Variable, cota_inferior: Variable, cota_superior: Variable):
        self.var = var
        self.variable_cota_inf = cota_inferior
        self.variable_cota_sup = cota_superior
        super().__init__(cota_inferior.cota_inferior, cota_superior.cota_superior)

    def valor(self) -> float:
        return max(self.variable_cota_inf.valor(), min(self.var.valor(), self.variable_cota_sup.valor()))

class VariableConTasaDeCambioConstante(Variable, Timer):
    def __init__(self, valor_inicial: float, cota_inferior: Variable, cota_superior: Variable, tasa_de_cambio_por_segundo: Variable):
        self._valor = valor_inicial
        self.tasa_de_cambio = tasa_de_cambio_por_segundo
        self.var_cota_inferior = cota_inferior
        self.var_cota_superior = cota_superior
        super().__init__(cota_inferior.cota_inferior, cota_superior.cota_superior)
        Timer.__init__(self)
    
    def tick(self):
        self._valor += self.tasa_de_cambio.valor() * Timer.TICK
        self._valor = max(self.var_cota_inferior.valor(), min(self._valor, self.var_cota_superior.valor())) # Acoto el valor a los límites definidos
    
    def valor(self) -> float:
        return self._valor

class VariableLambda(Variable):
    def __init__(self, funcion, cota_inferior: float, cota_superior: float):
        self.funcion = funcion
        super().__init__(cota_inferior, cota_superior)

    def valor(self) -> float:
        return self.funcion()
    
# Guarda adentro suyo una variable, que se puede modificar en tiempo de ejecución
class VariableMutable(Variable):
    def __init__(self, variable: Variable, cota_inferior: float, cota_superior: float):
        self.variable = variable.acotado(Constante(cota_inferior), Constante(cota_superior))
        super().__init__(cota_inferior, cota_superior)

    def valor(self) -> float:
        return self.variable.valor()
    
    def mutar(self, nueva_variable: Variable):
        if nueva_variable.cota_inferior != self.cota_inferior or nueva_variable.cota_superior != self.cota_superior:
            raise ValueError(f"La variable nueva no tiene los límites definidos originalmente para esta Variable Mutable. Originales: {self.variable.cota_inferior} y {self.variable.cota_superior}. Nuevos: {nueva_variable.cota_inferior} y {nueva_variable.cota_superior}")
        self.variable = nueva_variable

control_activado = False

def toggle_control():
    global control_activado
    control_activado = not control_activado

def iniciar_interfaz_control():
    root = tk.Tk()
    root.title("Control de Sistema")

    var_control = tk.BooleanVar(value=control_activado)
    checkbutton_control = tk.Checkbutton(root, text="Sistema de control activado", variable=var_control, command=toggle_control)
    checkbutton_control.pack(padx=20, pady=20)

    root.mainloop()

if __name__ == "__main__":
    # SISTEMA A CONTROLAR
    VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION = 180 # En radianes/segundo. Para neumáticos de diámetro 17 pulgadas, para ir a una velocidad máxima de 140hm/h: (38.8888 m/s) / ((17 / 39.37 / 2) m) = 180 rad/s
    CAPACIDAD_ACELERACION_LINEAL = 1.944444 # En m/s2. Nuestro auto iría de 0 a 140km/h, que es su velocidad máxima, en 20 segundos.
    CAPACIDAD_ACELERACION_DE_RUEDAS = 9 # Aceleración en giros por segundo que el auto le aplica a las ruedas, cuando el agarre es máximo. Es la CAPACIDAD_ACELERACION_LINEAL dividido por el radio de las ruedas, que es 17 / 39.37 / 2 = 0.216
    acelerador = VariableDeslizadorEnPantalla(Deslizador("Acelerador", minimo=0, maximo=1, inicial=0))
    agarreAsfalto = [VariableDeslizadorEnPantalla(Deslizador(f"Agarre Rueda {numero_de_rueda}", minimo=0, maximo=1, inicial=1)) for numero_de_rueda in [1,2,3,4] ]

    accionadorFrenos = [VariableMutable(Constante(0), 0, 1), VariableMutable(Constante(0), 0, 1), 
                        VariableMutable(Constante(0), 0, 1), VariableMutable(Constante(0), 0, 1)] # Al principio, seteamos la salida del sistema de control en 0, porque no tenemos todavía la primera medición

    # La velocidad de las ruedas se reduce por el agarre que tiene el asfalto. Cuanto más agarre tenga, más resistencia a la rotación
    # van a tener las ruedas, porque estas van a estar haciendo fuerza para cambiar la velocidad del auto.
    resistenciaAlAvance = Constante(1)
    aceleraciónRuedas = [VariableLambda(lambda agarre=agarre, freno=freno: 
                                        -100 if freno.valor() == 1 else 
                                        100 if agarre.valor() != 1 and acelerador.valor() > 0 
                                        else acelerador.valor() * CAPACIDAD_ACELERACION_DE_RUEDAS, 
                                    -100, 100) # La aceleración de las ruedas es proporcional a la posición del acelerador, pero si la rueda no tiene agarre, acelera un montón porque patina, y si está siendo frenada y tenemos pérdida de tracción, frena súper rápido
                        .menos(resistenciaAlAvance) 
        for agarre, freno in zip(agarreAsfalto, accionadorFrenos)] # Lo defino como aceleración - 1, para representar la resistencia al avance del auto, que se opone a la aceleración. Así, si dejamos el acelerador en un nivel inferior al 10%, la velocidad irá bajando

    VELOCIDAD_MINIMA_RUEDAS = 0  # La velocidad de las ruedas tiene como cota inferior 0 porque no contemplamos la posibilidad de que el auto pueda ir para atrás
    VELOCIDAD_MAXIMA_RUEDAS = VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION

    velocidadPromedioRuedas = VariableMutable(Constante(0), VELOCIDAD_MINIMA_RUEDAS, VELOCIDAD_MAXIMA_RUEDAS) # Al principio, seteamos la velocidad inicial 

    velocidadRuedas = [VariableConTasaDeCambioConstante(40,
                Constante(VELOCIDAD_MINIMA_RUEDAS), 
                VariableLambda(lambda agarre=agarre: velocidadPromedioRuedas.valor() if agarre.valor() == 1 else VELOCIDAD_MAXIMA_RUEDAS, VELOCIDAD_MINIMA_RUEDAS, VELOCIDAD_MAXIMA_RUEDAS), 
                aceleracion)
        for aceleracion, agarre in zip(aceleraciónRuedas, agarreAsfalto)]

    # SISTEMA DE CONTROL
    PROPAGACION_TACOMETRO = 0.5 # tiempo que se tarda en medir la velodicad de las ruedas
    medicionesVelocidadesRuedas = [velocidad.retardado(PROPAGACION_TACOMETRO) for velocidad in velocidadRuedas]
    velocidadPromedioRuedas.mutar(VariableLambda(lambda: sum([medicion.valor() for medicion in medicionesVelocidadesRuedas]) / len(medicionesVelocidadesRuedas), VELOCIDAD_MINIMA_RUEDAS, VELOCIDAD_MAXIMA_RUEDAS))

    for accionadorFrenoRueda, medicionVelocidadRueda in zip(accionadorFrenos, medicionesVelocidadesRuedas): # Ahora que ya tenemos la primer medición, creamos el ciclo de realimentación
        def crear_lambda(medicion):
            return lambda medicion=medicion: 1 if control_activado and medicion.valor() > velocidadPromedioRuedas.valor() * 2 else 0
        accionadorFrenoRueda.mutar(VariableLambda(crear_lambda(medicionVelocidadRueda), 0, 1))

    graficos = {
        "a": Constante(0), #Después se van a pisar cuando haga el agregar_gráficos_múltiples. Sí, es feo.
        "b": Constante(0),
        "c": Constante(0),
        "d": Constante(0),
        "Acelerador": acelerador,
        "Agarre Rueda 1": agarreAsfalto[0],
        "Agarre Rueda 2": agarreAsfalto[1],
        "Agarre Rueda 3": agarreAsfalto[2],
        "Agarre Rueda 4": agarreAsfalto[3],
        "Velocidad Promedio Ruedas": velocidadPromedioRuedas,
        "Accionador Frenos 1": accionadorFrenos[0],
        "Accionador Frenos 2": accionadorFrenos[1],
        "Accionador Frenos 3": accionadorFrenos[2],
        "Accionador Frenos 4": accionadorFrenos[3],
        "Aceleración Rueda 1": aceleraciónRuedas[0],
        "Aceleración Rueda 2": aceleraciónRuedas[1],
        "Aceleración Rueda 3": aceleraciónRuedas[2],
        "Aceleración Rueda 4": aceleraciónRuedas[3],
    }

    graficos = Graficos(titulo="Señales en tiempo real", graficos=graficos, ventana_temporal=10)
    graficos.agregar_graficos_multiples([
        ("Velocidad Rueda 1", [("Real", velocidadRuedas[0]), ("Medición", medicionesVelocidadesRuedas[0])]),
        ("Velocidad Rueda 2", [("Real", velocidadRuedas[1]), ("Medición", medicionesVelocidadesRuedas[1])]),
        ("Velocidad Rueda 3", [("Real", velocidadRuedas[2]), ("Medición", medicionesVelocidadesRuedas[2])]),
        ("Velocidad Rueda 4", [("Real", velocidadRuedas[3]), ("Medición", medicionesVelocidadesRuedas[3])])
    ])
    
    # Iniciar la interfaz de control en otro hilo
    threading.Thread(target=iniciar_interfaz_control, daemon=True).start()
    
    graficos.iniciar(int(Timer.TICK * 1000))