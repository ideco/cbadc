"""Analog System and Digital Control Simulator

This module provides simulator tools to simulate the hardware
interaction between an analog system and digital control.
These are mainly intended to produce control signals
:math:`\mathbf{s}[k]` and evaluate state vector trajectories
:math:`\mathbf{x}(t)` for various Analog system
:py:class:`cbadc.analog_system.AnalogSystem` and
:py:class:`cbadc.digital_control.DigitalControl` interactions.
"""
from .analog_system import AnalogSystem
from .digital_control import DigitalControl
from .analog_signal import AnalogSignal, ConstantSignal, Sinusodial
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm
import math
from typing import Iterator, Generator, List, Dict, Union


class StateSpaceSimulator(Iterator[np.ndarray]):
    """Simulate the analog system and digital control interactions
    in the presence on analog signals.

    Parameters
    ----------
    analog_system : :py:class:`cbadc.analog_system.AnalogSystem`
        the analog system
    digital_control: :py:class:`cbadc.digital_control.DigitalControl`
        the digital control
    input_signals : [:py:class:`cbadc.analog_signal.AnalogSignal`]
        a python list of analog signals (or a derived class)
    Ts : `float`, optional
        specify a sampling rate at which we want to evaluate the systems
        , defaults to :py:class:`digitalControl.Ts`. Note that this Ts must be smaller
        than :py:class:`digitalControl.Ts`.
    t_stop : `float`, optional
        determines a stop time, defaults to :py:obj:`math.inf`



    Attributes
    ----------
    analog_system : :py:class:`cbadc.analog_system.AnalogSystem`
        the analog system being simulated.
    digital_control : :py:class:`cbadc.digital_control.DigitalControl`
        the digital control being simulated.
    t : `float`
        current time of simulator.
    Ts : `float`
        sample rate of simulation.
    t_stop : `float`
        end time at which the generator raises :py:class:`StopIteration`.
    rtol, atol : `float`, `optional`
        Relative and absolute tolerances. The solver keeps the local error estimates less
        than atol + rtol * abs(y). Effects the underlying solver as described in
        :py:func:`scipy.integrate.solve_ivp`. Default to 1e-3 for rtol and 1e-6 for atol.
    max_step : `float`, `optional`
        Maximum allowed step size. Default is np.inf, i.e., the step size is not
        bounded and determined solely by the solver. Effects the underlying solver as
        described in :py:func:`scipy.integrate.solve_ivp`. Defaults to :py:obj:`math.inf`.
    See also
    --------
    :py:class:`cbadc.analog_signal.AnalogSignal`
    :py:class:`cbadc.analog_system.AnalogSystem`
    :py:class:`cbadc.digital_control.DigitalControl`

    Examples
    --------
    >>> from cbadc.simulator import StateSpaceSimulator
    >>> from cbadc.analog_signal import Sinusodial
    >>> from cbadc.analog_system import AnalogSystem
    >>> from cbadc.digital_control import DigitalControl
    >>> import numpy as np
    >>> A = np.array([[0., 0], [6250., 0.]])
    >>> B = np.array([[6250., 0]]).transpose()
    >>> CT = np.array([[1, 0], [0, 1]])
    >>> Gamma = np.array([[-6250, 0], [0, -6250]])
    >>> Gamma_tildeT = CT
    >>> analog_system = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    >>> digital_control = DigitalControl(1e-6, 2)
    >>> input_signal = Sinusodial(1.0, 250)
    >>> simulator = StateSpaceSimulator(analog_system, digital_control, (input_signal,))
    >>> _ = simulator.__next__()
    >>> _ = simulator.__next__()
    >>> print(np.array(simulator.__next__()))
    [0 0]

    See also
    --------

    Yields
    ------
    `array_like`, shape=(M,), dtype=numpy.int8

    Raises
    ------
    str : unknown

    """

    def __init__(self,
                 analog_system: AnalogSystem,
                 digital_control: DigitalControl,
                 input_signal: List[Union[AnalogSignal, ConstantSignal,
                                          Sinusodial]],
                 Ts: float = None,
                 t_stop: float = math.inf,
                 atol: float = 1e-12,
                 rtol: float = 1e-12,
                 max_step: float = math.inf,
                 ):
        if analog_system.L != len(input_signal):
            raise BaseException("""The analog system does not have as many inputs as in input
            list""")
        self.analog_system = analog_system
        self.digital_control = digital_control
        self.input_signals = input_signal
        self.t: float = 0.
        self.t_stop = t_stop
        if Ts:
            self.Ts = Ts
        else:
            self.Ts = self.digital_control.T
        if self.Ts > self.digital_control.T:
            raise BaseException(
                f"Simulating with a sample period {self.Ts} that exceeds the control period of the digital control {self.digital_control.T}")
        self._state_vector = np.zeros(self.analog_system.N, dtype=np.double)
        self._temp_state_vector = np.zeros(
            self.analog_system.N, dtype=np.double)
        self._control_observation = np.zeros(
            self.analog_system.M_tilde, dtype=np.double)
        self._input_vector = np.zeros(self.analog_system.L, dtype=np.double)
        self._control_vector = np.zeros(self.analog_system.M, dtype=np.double)
        self._res = np.zeros(self.analog_system.N, dtype=np.double)
        self.atol = atol  # 1e-6
        self.rtol = rtol  # 1e-6
        if (max_step > self.Ts):
            self.max_step = self.Ts / 1e-1
        else:
            self.max_step = max_step
        self._pre_computations()
        # self.solve_oder = self._ordinary_differential_solution
        # self.solve_oder = self._full_ordinary_differential_solution

    def state_vector(self) -> np.ndarray:
        """return current analog system state vector :math:`\mathbf{x}(t)`
        evaluated at time :math:`t`.

        Examples
        --------
        >>> from cbadc.simulator import StateSpaceSimulator
        >>> from cbadc.analog_signal import Sinusodial
        >>> from cbadc.analog_system import AnalogSystem
        >>> from cbadc.digital_control import DigitalControl
        >>> import numpy as np
        >>> A = np.array([[0., 0], [6250., 0.]])
        >>> B = np.array([[6250., 0]]).transpose()
        >>> CT = np.array([[1, 0], [0, 1]])
        >>> Gamma = np.array([[-6250, 0], [0, -6250]])
        >>> Gamma_tildeT = CT
        >>> analog_system = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
        >>> digital_control = DigitalControl(1e-6, 2)
        >>> input_signal = Sinusodial(1.0, 250)
        >>> simulator = StateSpaceSimulator(analog_system, digital_control, (input_signal,))
        >>> _ = simulator.__next__()
        >>> _ = simulator.__next__()
        >>> print(np.array(simulator.state_vector()))
        [-0.00623036 -0.00626945]

        Returns
        -------
        `array_like`, shape=(N,)
            returns the state vector :math:`\mathbf{x}(t)`
        """
        return self._state_vector[:]

    def __iter__(self):
        """Use simulator as an iterator
        """
        return self

    def __next__(self) -> np.ndarray:
        """Computes the next control signal :math:`\mathbf{s}[k]`
        """
        t_end: float = self.t + self.Ts
        t_span = np.array((self.t, t_end))
        if t_end >= self.t_stop:
            raise StopIteration
        self._state_vector = self._ordinary_differential_solution(t_span)
        # self._state_vector = self._full_ordinary_differential_solution(t_span)
        self.t = t_end
        return self.digital_control.control_signal()

    def _analog_system_matrix_exponential(self, t: float) -> np.ndarray:
        return np.asarray(expm(np.asarray(self.analog_system.A) * t))

    def _pre_computations(self):
        """Precomputes quantities for quick evaluation of state transition and control
        contribution.

        Specifically,

        :math:`\exp\\left(\mathbf{A} T_s \\right)`

        and

        :math:`\mathbf{A}_c = \int_{0}^{T_s} \exp\\left(\mathbf{A} (T_s - \tau)\\right) \mathbf{\Gamma} \mathbf{d}(\tau) \mathrm{d} \tau`

        are computed where the formed describes the state transition and the latter
        the control contributions. Furthermore, :math:`\mathbf{d}(\tau)` is the DAC waveform
        (or impulse response) of the digital control.
        """

        # expm(A T_s)
        self._pre_computed_state_transition_matrix = self._analog_system_matrix_exponential(
            self.Ts)

        def derivative(t, x):
            dac_waveform = np.zeros(
                (self.analog_system.M, self.analog_system.M))
            for m in range(self.analog_system.M):
                dac_waveform[:, m] = self.digital_control.impulse_response(
                    m, t)
            return np.dot(
                np.asarray(
                    self._analog_system_matrix_exponential(self.Ts - t)),
                np.dot(np.asarray(self.analog_system.Gamma),
                       dac_waveform)
            ).flatten()

        tspan = np.array([0, self.Ts])
        atol = 1e-12
        rtol = 1e-12
        max_step = self.Ts * 1e-3

        self._pre_computed_control_matrix = solve_ivp(derivative,
                                                      tspan,
                                                      np.zeros(
                                                          (self.analog_system.N * self.analog_system.M)),
                                                      atol=atol, rtol=rtol, max_step=max_step
                                                      ).y[:, -1].reshape((self.analog_system.N, self.analog_system.M), order='C')

    def _ordinary_differential_solution(self, t_span: np.ndarray) -> np.ndarray:
        """Computes system ivp in three parts:

        First solve input signal contribution by computing

        :math:`\mathbf{u}_{c} = \int_{t_1}^{t_2} \mathbf{A} x(t) + \mathbf{B} \mathbf{u}(t) \mathrm{d} t`

        where :math:`\mathbf{x}(t_1) = \begin{pmatrix} 0, & \dots, & 0 \end{pmatrix}^{\mathsf{T}}`.

        Secondly advance the previous state as

        :math:`\mathbf{x}_c = \mathbf{x}(t_2) = \exp\\left( \mathbf{A} T_s \\right) \mathbf{x}(t_1)`

        Thirdly, compute the control contribution by

        :math:`\mathbf{s}_c = \mathbf{A}_c \mathbf{s}[k]`

        where :math:`\mathbf{A}_c = \int_{0}^{T_s} \exp\\left(\mathbf{A} (T_s - \tau)\\right) \mathbf{\Gamma} \mathbf{d}(\tau) \mathrm{d} \tau`
        and :math:`\mathbf{d}(\tau)` is the DAC waveform (or impulse response) of the digital control.

        Finally, all contributions are added and returned as

        :math:`\mathbf{u}_{c} + \mathbf{x}_c + \mathbf{s}_c`.

        Parameters
        ----------
        t_span : (float, float)
            the initial time :math:`t_1` and end time :math:`t_2` of the simulations.

        Returns
        -------
        array_like, shape=(N,)
            computed state vector.
        """

        # Compute signal contribution
        def f(t, x):
            return self._signal_derivative(t, x)
        self._temp_state_vector = solve_ivp(
            f,
            t_span,
            np.zeros(self.analog_system.N),
            atol=self.atol,
            rtol=self.rtol,
            max_step=self.max_step
        ).y[:, -1]

        self._temp_state_vector += np.dot(
            self._pre_computed_state_transition_matrix, self._state_vector).flatten()

        # Compute control observation s_tilde(t)
        self._control_observation = np.dot(
            self.analog_system.Gamma_tildeT, self._state_vector)

        # update control at time t_span[0]
        self._char_control_vector = self.digital_control.control_contribution(
            t_span[0], self._control_observation)
        self._temp_state_vector += np.dot(
            self._pre_computed_control_matrix, self._char_control_vector).flatten()
        return self._temp_state_vector

    def _signal_derivative(self, t: float, x: np.ndarray) -> np.ndarray:
        res = np.dot(self.analog_system.A, x)
        for _l in range(self.analog_system.L):
            res += np.dot(self.analog_system.B[:, _l],
                          self.input_signals[_l].evaluate(t))
        return res.flatten()

    def _full_ordinary_differential_solution(self, t_span: np.ndarray) -> np.ndarray:
        return solve_ivp(
            lambda t, x: self._ordinary_differentail_function(t, x),
            t_span,
            self._state_vector,
            atol=self.atol,
            rtol=self.rtol,
            max_step=self.max_step
        ).y[:, -1]

    def _ordinary_differentail_function(self, t: float, y: np.ndarray):
        """Solve the differential computational problem
        of the analog system and digital control interaction

        Parameters
        ----------
        t : `float`
            the time for evaluation
        y : array_lik, shape=(N,)
            state vector

        Returns
        -------
        array_like, shape=(N,)
            vector of derivatives evaluated at time t.
        """
        for _l in range(self.analog_system.L):
            self._input_vector[_l] = self.input_signals[_l].evaluate(t)
        self._temp_state_vector = np.dot(self.analog_system.Gamma_tildeT, y)
        self._control_vector = self.digital_control.control_contribution(
            t, self._temp_state_vector)
        return np.asarray(self.analog_system.derivative(self._temp_state_vector, t, self._input_vector, self._control_vector)).flatten()

    def __str__(self):
        return f"t = {self.t}, (current simulator time)\nTs = {self.Ts},\nt_stop = {self.t_stop},\nrtol = {self.rtol},\natol = {self.atol}, and\nmax_step = {self.max_step}\n"


def extended_simulation_result(simulator: StateSpaceSimulator) -> Generator[Dict[str, np.ndarray], None, None]:
    """Extended simulation output

    Used to also pass the state vector from a
    simulator generator.

    Parameters
    ----------
    simulator : :py:class:`cbadc.simulator.StateSpaceSimulator`
        a iterable simulator instance.

    Yields
    ------
    { 'control_signal', 'analog_state' } : { (array_like, shape=(M,)), (array_like, shape=(N,)) }
        an extended output including the analog state vector.
    """
    for control_signal in simulator:
        analog_state = simulator.state_vector()
        yield {
            'control_signal': np.array(control_signal),
            'analog_state': np.array(analog_state)
        }
