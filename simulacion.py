import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import defaultdict
from abc import ABC, abstractmethod
from typing import Callable, Dict, Mapping, List, Tuple
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
        """/
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
    
    def transformada(self, funcion: Callable[[float], float], cota_inferior, cota_superior) -> 'Variable':
        return VariableLambda(lambda: funcion(self.valor()), cota_inferior, cota_superior)
    
    def mayor(self, otra: 'Variable') -> bool:
        return self.valor() > otra.valor()
    
    def menor(self, otra: 'Variable') -> bool:
        return self.valor() < otra.valor()
    
    def igual(self, otra: 'Variable') -> bool:
        return self.valor() == otra.valor()

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

# Type aliases for better readability
VariableGraficada = Tuple[str, Variable] # Una variable con su nombre
Grafico = Tuple[str, List[VariableGraficada]] # Una lista de variables a graficar en un mismo eje cartesiano, y el nombre del gráfico
Renglon = List
GrillaGraficos = List[Renglon[Grafico]]

class Graficos:
    """
    Grafica la evolución temporal de una cantidad arbitraria de variables.
    """
    def __init__(self, titulo: str = "", 
                 x_label: str = "Tiempo", y_label: str = "Valor", 
                 x_lim: int = 100, ventana_temporal_en_segundos: int = 10, 
                 graficos: GrillaGraficos = []):
        """
        Inicializa el gráfico con múltiples subplots y configura las fuentes de datos directamente.

        :param titulo: Título del gráfico principal.
        :param xLabel: Etiqueta del eje X.
        :param yLabel: Etiqueta del eje Y.
        :param xLim: Límite del eje X.
        :param ventanaTemporalEnSegundos: Duración de la ventana temporal en segundos.
        :param graficos: Lista de listas, de gráficos. Cada lista de segundo nivel (lista adentro de la lista que contiene todo) define un nuevo renglón en la grilla donde se mostrarán gráficos. Cada gráfico es una tupla (descripción, [(etiqueta, variable)]). Agregar varios (etiqueta, variable) en un mismo gráfico permite graficar varias variables en un mismo eje cartesiano.
        """
        self.titulo = titulo
        self.x_label = x_label
        self.y_label = y_label
        self.x_lim = x_lim
        self.ventana_temporal = ventana_temporal_en_segundos
        self.layout = graficos or [[]]
        self.filas = len(self.layout)
        self.columnas = max(len(row) for row in self.layout)
        self.fuentes: Dict[str, Variable] = {}
        self.variables: List[str] = []
        self.x_data: List[int] = []
        self.y_data: Dict[str, List[float]] = defaultdict(list)
        self.frame = 0

        self.fig, self.axes = plt.subplots(self.filas, self.columnas, figsize=(12, 12))
        self.axes = self.axes.flatten()

        for i in range(self.filas * self.columnas):
            self.axes[i].axis('off')

        self.lines: Dict = {}
        self.fig.suptitle(f"{titulo} (últimos {ventana_temporal_en_segundos} segundos)")
        plt.subplots_adjust(hspace=0.5, wspace=0.5)

        self._configurar_graficos()

    def _configurar_graficos(self):
        colores = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'cyan', 'magenta']
        for i, fila in enumerate(self.layout):
            for j, (titulo, variables) in enumerate(fila):
                ax = self.axes[i * self.columnas + j]
                ax.set_xlim(0, self.x_lim)
                if all(isinstance(var, Variable) for var in variables):
                    ax.set_ylim(min(var.cota_inferior for var in variables),  # type: ignore porque ya chequeé los tipos en el if de arriba
                                max(var.cota_superior for var in variables))  # type: ignore porque ya chequeé los tipos en el if de arriba
                else:
                    ax.set_ylim(min(var.cota_inferior for _, var in variables), 
                                max(var.cota_superior for _, var in variables))
                for k, variable in enumerate(variables):
                    if isinstance(variable, tuple):
                        etiqueta, variable = variable
                    else:
                        etiqueta = None
                    nombre_variable = f"{titulo} - {etiqueta}" if etiqueta else titulo
                    self.fuentes[nombre_variable] = variable
                    line, = ax.plot([], [], lw=2, label=etiqueta if etiqueta else "", color=colores[k % len(colores)])
                    self.lines[nombre_variable] = line
                if any(isinstance(variable, tuple) for variable in variables):
                    ax.legend()
                ax.set_title(titulo)
                ax.set_xlabel(self.x_label)
                ax.set_ylabel(self.y_label)
                ax.set_xticklabels([])  # Remove numerical indicators from X-axis
                ax.axis('on')
                self.variables.append(titulo)
        plt.subplots_adjust(hspace=0.7, wspace=0.5)

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
        return list(self.lines.values())

    def iniciar(self, interval: int = 100) -> None:
        """
        Inicia la animación del gráfico.
        :param interval: Tiempo en milisegundos entre cada actualización.
        """
        def actualizar_y_graficar(_):
            self.actualizar_datos()
            return self.actualizar(_)
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
        self._valor: float = valor_inicial
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
    def __init__(self, funcion: Callable[[], float], cota_inferior: float, cota_superior: float):
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

class VariableQueReaccionaAlCambio(Variable, Timer):
    def __init__(self, variable_que_trackeo: Variable, cambio_al_que_reacciono: Callable[[float, float], bool], 
                 valor_cuando_hubo_un_cambio: Variable, valor_normal: Variable):
        self.variable_que_trackeo = variable_que_trackeo
        self.cambio_al_que_reacciono = cambio_al_que_reacciono
        self.valor_normal = valor_normal
        self.valor_cuando_hubo_un_cambio = valor_cuando_hubo_un_cambio
        self.valor_anterior = variable_que_trackeo.valor()
        self.hubo_cambio = False
        Variable.__init__(self, min(valor_normal.cota_inferior, valor_cuando_hubo_un_cambio.cota_inferior), max(valor_normal.cota_superior, valor_cuando_hubo_un_cambio.cota_superior))
        Timer.__init__(self)

    def valor(self) -> float:
        if (self.hubo_cambio):
            self.hubo_cambio = False # hubo_cambio solo se setea el False cuando se pide un valor a esta variable. Así, me aseguro de que todo cambio en la variable trackeada, tenga un impacto en esta.
            return self.valor_cuando_hubo_un_cambio.valor()
        else:
            return self.valor_normal.valor()
        
    def tick(self):
        self.hubo_cambio |= self.cambio_al_que_reacciono(self.valor_anterior, self.variable_que_trackeo.valor()) # Si hubo_cambio es True, sigue siendo True. Si es False, lo seteo en True si ocurrió el cambio al que reacciono en el último tick
        self.valor_anterior = self.variable_que_trackeo.valor() # Actualizo el valor anterior

class VariableIf(Variable):
    def __init__(self, condicion: Callable[[], bool], valor_si_cierto: Variable, valor_si_falso: Variable):
        self.condicion = condicion
        self.valor_si_cierto = valor_si_cierto
        self.valor_si_falso = valor_si_falso
        super().__init__(min(valor_si_cierto.cota_inferior, valor_si_falso.cota_inferior), max(valor_si_cierto.cota_superior, valor_si_falso.cota_superior))

    def valor(self) -> float:
        return self.valor_si_cierto.valor() if self.condicion() else self.valor_si_falso.valor()

class InterruptorControlTraccion:
    def __init__(self):
        self.activado = False
        self.iniciar_en_hilo_paralelo()

    def iniciar_en_hilo_paralelo(self):
        threading.Thread(target=self.abrir_interruptor, daemon=True).start()
    
    def toggle_control(self):
        self.activado = not self.activado

    def abrir_interruptor(self):
        root = tk.Tk()
        root.title("Control de Sistema")

        var_control = tk.BooleanVar(value=self.activado)
        checkbutton_control = tk.Checkbutton(root, text="Sistema de control activado", variable=var_control, command=self.toggle_control)
        checkbutton_control.pack(padx=20, pady=20)

        root.mainloop()

if __name__ == "__main__":
    # CONSTANTES FÍSICAS QUE DEPENDEN DE LAS CARATERÍSTICAS TÉCNICAS DEL AUTOMÓVIL
    VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION = 180 # En radianes/segundo. Para neumáticos de diámetro 17 pulgadas, para ir a una velocidad máxima de 140hm/h: (38.8888 m/s) / ((17 / 39.37 / 2) m) = 180 rad/s
    CAPACIDAD_ACELERACION_LINEAL = 1.944444 # En m/s2. Nuestro auto iría de 0 a 140km/h, que es su velocidad máxima, en 20 segundos.
    CAPACIDAD_ACELERACION_DE_RUEDAS = 9 # Aceleración en giros por segundo que el auto le aplica a las ruedas, cuando el agarre es máximo. Es la CAPACIDAD_ACELERACION_LINEAL dividido por el radio de las ruedas, que es 17 / 39.37 / 2 = 0.216
    RESISTENCIA_AL_AVANCE = 1 # En m/s2. La resistencia al avance que cada rueda experimenta. Es un frenado constante que se opone al avance del auto, por sus características aerodinámicas y resistencias de los componentes mecánicos.
    VELOCIDAD_MAXIMA_RUEDAS = VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION * 5 # Cuando pierden tracción, las ruedas giran libres, alcanzando velocidades mucho más altas, porque ya no tienen la resistencia del auto.
    PROPAGACION_TACOMETRO = 0.5 # tiempo que se tarda en medir la velodicad de las ruedas
    
    # CONTROLES DEL AUTOMÓVIL (ENTRADAS)
    # ACELERADOR
    acelerador = VariableDeslizadorEnPantalla(Deslizador("Acelerador", minimo=0, maximo=1, inicial=0))
    # ACTIVA O DESACTIVA EL CONTROL DE TRACCIÓN EN EL CONTROLADOR
    interruptor_control_traccion = InterruptorControlTraccion() 
    
    # PÉRDIDAS DE TRACCIÓN / RUIDO. 1 es agarre perfecto, 0 es pérdida total de tracción. Por defecto es 1, y se puede reducir manualmente para ver la respuesta del sistema.
    agarre_asfalto = [VariableDeslizadorEnPantalla(Deslizador(f"Agarre Rueda {numero_de_rueda}", minimo=0, maximo=1, inicial=1)) for numero_de_rueda in [1,2,3,4] ]
 
    # ACTUADOR DEL FRENO, Y FRENO
    # Seteamos inicialmente en 0, porque no tenemos ninguna medición. # TODO: CAMBIANDO EL ORDEN NO SE PUEDE HACER QUE ESTO DEJE DE SER NECESARIO?
    actuador_frenos = [VariableMutable(Constante(0), 0, 1) for _ in range(4)]

    # TORQUE APLICADO SOBRE LAS RUEDAS
    # La velocidad de las ruedas se reduce por el agarre que tiene el asfalto. Cuanto más agarre tenga, más resistencia a la rotación van a tener las ruedas, porque estas van a estar haciendo fuerza para cambiar la velocidad del auto.
    aceleracion_ruedas = [VariableLambda(lambda agarre=agarre, freno=freno: 
                                        -100 if freno.valor() == 1 else # Si estoy frenando
                                        50 if agarre.valor() != 1 and acelerador.valor() > 0 # Si estoy acelerando y no tengo agarre
                                        else acelerador.valor() * CAPACIDAD_ACELERACION_DE_RUEDAS, # Situación de agarre normal
                                    -100, 100) # La aceleración de las ruedas es proporcional a la posición del acelerador, pero si la rueda no tiene agarre, acelera un montón porque patina, y si está siendo frenada y tenemos pérdida de tracción, frena súper rápido
                        .menos(Constante(RESISTENCIA_AL_AVANCE)) 
        for agarre, freno in zip(agarre_asfalto, actuador_frenos)] # Lo defino como aceleración - 1, para representar la resistencia al avance del auto, que se opone a la aceleración. Así, si dejamos el acelerador en un nivel inferior al 10%, la velocidad irá bajando

    def velocidad_promedio_otras_ruedas(medicion, velocidades):
        return (sum([medicion.valor() for medicion in velocidades]) - medicion.valor()) / (len(velocidades) - 1)

    # TACÓMETRO
    # Inicializada en 0 porque en el primer ciclo no contamos con la medición
    mediciones_velocidades_ruedas = [VariableMutable(Constante(0), 0, VELOCIDAD_MAXIMA_RUEDAS) for _ in range(4)]

    # VELOCIDAD DE LAS RUEDAS (SALIDA DEL SISTEMA)
    # Comienza siendo 0
    velocidad_ruedas = [VariableMutable(Constante(0), 0, VELOCIDAD_MAXIMA_RUEDAS) for _ in range(4)]

    # CÁLCULO REALIZADO POR EL ECU
    velocidades_promedio_otras_ruedas = [
        VariableLambda(lambda medicion=medicion: velocidad_promedio_otras_ruedas(medicion, mediciones_velocidades_ruedas), 0, VELOCIDAD_MAXIMA_RUEDAS) 
        for medicion in mediciones_velocidades_ruedas]

    # COMPORTAMIENTO FÍSICO RUEDAS Y COCHE
    # Normalmente, las ruedas tienen un límite de velocidad igual a VELOCIDAD_MAXIMA_RUEDAS
    # Pero cuando una rueda que estaba girando libre retoma la tracción, esta vuelve a girar a la velocidad de las otras ruedas
    velocidades_limite_ruedas: List[Variable] = [
        VariableQueReaccionaAlCambio(variable_que_trackeo = traccion, 
                                     cambio_al_que_reacciono = lambda traccion_anterior, traccion_actual: traccion_anterior < 1 and traccion_actual == 1, # Cuando se recupera la tracción
                                     valor_cuando_hubo_un_cambio = VariableLambda(lambda velocidad=velocidad, velocidad_ruedas=velocidad_ruedas: velocidad_promedio_otras_ruedas(velocidad, velocidad_ruedas), 0, VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION), # Limito la velocidad de cada rueda a la velocidad promedio de las otras ruedas. Esto hace que cuando una rueda está sin agarre, si luego vuelve a estar tener tracción, retome inmediatamente la velocidad del resto. Así es como ocurre en la realidad.
                                     valor_normal = VariableLambda(lambda traccion=traccion: VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION if traccion.valor() == 1 else VELOCIDAD_MAXIMA_RUEDAS, VELOCIDAD_MAXIMA_RUEDAS_CON_TRACCION, VELOCIDAD_MAXIMA_RUEDAS)) # Si no, la limito solamente con la velocidad máxima 'normal'
        for velocidad, traccion in zip(velocidad_ruedas, agarre_asfalto)]

    # Defino estas variables, que antes había inicializado en 0
    for velocidad, velocidad_limite, aceleracion in zip(velocidad_ruedas, velocidades_limite_ruedas, aceleracion_ruedas):
        velocidad.mutar(VariableConTasaDeCambioConstante(0, Constante(0), velocidad_limite, aceleracion))
    for medicion, velocidad in zip(mediciones_velocidades_ruedas, velocidad_ruedas):
        medicion.mutar(velocidad.retardado(PROPAGACION_TACOMETRO))

    # CONTROLADOR
    # Oportunidad de mejora: si quisiéramos que el control funcionase mejor cuando hay varias ruedas con pérdida de tracción, podríamos, antes de tomar la velocidad promedio de las otras ruedas, filtrar los 'outliers', es decir, las ruedas que tengan velocidades muy distintas al resto, que necesariamente están en situaciones de pérdida de tracción.
    def control_traccion(medicion_velocidad_rueda, interruptor_control_traccion, mediciones_velocidades_ruedas):
        return lambda: interruptor_control_traccion.activado and medicion_velocidad_rueda.mayor(Constante(velocidad_promedio_otras_ruedas(medicion_velocidad_rueda, mediciones_velocidades_ruedas)* 1.5)) # Frena la rueda si su velocidad supera en más de 50 por ciento el promedio de las velocidades medidas para las otras ruedas

    # ACTUADOR DEL FRENO, Y FRENO
    # Defino esta variables, que antes había inicializado en 0
    for accionador_freno_rueda, medicion_velocidad_rueda in zip(actuador_frenos, mediciones_velocidades_ruedas): # Ahora que ya tenemos la primer medición, creamos el ciclo de realimentación
        accionador_freno_rueda.mutar(VariableIf(control_traccion(medicion_velocidad_rueda, interruptor_control_traccion, mediciones_velocidades_ruedas), Constante(1), Constante(0)))

    gráficos = [
        [(f"Velocidad Rueda {i+1}", [("Real (θo)", velocidad_ruedas[i]), ("Medición (f, realimentacion)", mediciones_velocidades_ruedas[i])]) for i in range(4)], # Fila 1
        [(f"Aceleración Rueda {i+1}", [aceleracion_ruedas[i]]) for i in range(4)], # Fila 2
        [(f"Agarre Rueda {i+1} (Perturbación)", [agarre_asfalto[i]]) for i in range(4)], # Fila 3
        [(f"Actuador Frenos {i+1} (Actuador)", [actuador_frenos[i]]) for i in range(4)], # Fila 4
        [(f"Velocidad otras ruedas (θi rueda {i+1})", [velocidades_promedio_otras_ruedas[i]]) for i in range(4)], # Fila 5
        [("Acelerador (Entrada del usuario)", [acelerador])] # Fila 6
    ]

    graficos = Graficos(titulo="", ventana_temporal_en_segundos=10, graficos=gráficos)

    graficos.iniciar(int(Timer.TICK * 1000))