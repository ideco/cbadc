
.. DO NOT EDIT.
.. THIS FILE WAS AUTOMATICALLY GENERATED BY SPHINX-GALLERY.
.. TO MAKE CHANGES, EDIT THE SOURCE PYTHON FILE:
.. "auto_examples/a_getting_started/plot_c_digital_estimator.py"
.. LINE NUMBERS ARE GIVEN BELOW.

.. only:: html

    .. note::
        :class: sphx-glr-download-link-note

        Click :ref:`here <sphx_glr_download_auto_examples_a_getting_started_plot_c_digital_estimator.py>`
        to download the full example code

.. rst-class:: sphx-glr-example-title

.. _sphx_glr_auto_examples_a_getting_started_plot_c_digital_estimator.py:


Digital Estimation
===================

Converting a stream of control signals into a estimate samples.

.. GENERATED FROM PYTHON SOURCE LINES 7-17

.. code-block:: default
   :lineno-start: 7

    from cbadc.utilities import compute_power_spectral_density
    import matplotlib.pyplot as plt
    from cbadc.utilities import read_byte_stream_from_file, \
        byte_stream_2_control_signal
    from cbadc.utilities import random_control_signal
    from cbadc.analog_system import AnalogSystem
    from cbadc.digital_control import DigitalControl
    from cbadc.digital_estimator import DigitalEstimator
    import numpy as np








.. GENERATED FROM PYTHON SOURCE LINES 18-30

Setting up the Analog System and Digital Control
------------------------------------------------

In this example, we assume that we have access to a control signal
s[k] generated by the interactions of an analog system and digital control.
Furthermore, we assume a chain-of-integrators converter with corresponding
analog system and digital control.

.. image:: /images/chainOfIntegratorsGeneral.svg
   :width: 500
   :align: center
   :alt: The chain of integrators ADC.

.. GENERATED FROM PYTHON SOURCE LINES 30-61

.. code-block:: default
   :lineno-start: 31


    # Setup analog system and digital control

    N = 6
    M = N
    beta = 6250.
    rho = - beta * 1e-2
    A = [[rho, 0, 0, 0, 0, 0],
         [beta, rho, 0, 0, 0, 0],
         [0, beta, rho, 0, 0, 0],
         [0, 0, beta, rho, 0, 0],
         [0, 0, 0, beta, rho, 0],
         [0, 0, 0, 0, beta, rho]]
    B = [[beta], [0], [0], [0], [0], [0]]
    CT = np.eye(N)
    Gamma = [[-beta, 0, 0, 0, 0, 0],
             [0, -beta, 0, 0, 0, 0],
             [0, 0, -beta, 0, 0, 0],
             [0, 0, 0, -beta, 0, 0],
             [0, 0, 0, 0, -beta, 0],
             [0, 0, 0, 0, 0, -beta]]
    Gamma_tildeT = np.eye(N)
    T = 1.0/(2 * beta)

    analog_system = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    digital_control = DigitalControl(T, M)

    # Summarize the analog system, digital control, and digital estimator.
    print(analog_system, "\n")
    print(digital_control)





.. rst-class:: sphx-glr-script-out

 Out:

 .. code-block:: none

    The analog system is parameterized as:
    A =
    [[ -62.5    0.     0.     0.     0.     0. ]
     [6250.   -62.5    0.     0.     0.     0. ]
     [   0.  6250.   -62.5    0.     0.     0. ]
     [   0.     0.  6250.   -62.5    0.     0. ]
     [   0.     0.     0.  6250.   -62.5    0. ]
     [   0.     0.     0.     0.  6250.   -62.5]],
    B =
    [[6250.]
     [   0.]
     [   0.]
     [   0.]
     [   0.]
     [   0.]],
    CT = 
    [[1. 0. 0. 0. 0. 0.]
     [0. 1. 0. 0. 0. 0.]
     [0. 0. 1. 0. 0. 0.]
     [0. 0. 0. 1. 0. 0.]
     [0. 0. 0. 0. 1. 0.]
     [0. 0. 0. 0. 0. 1.]],
    Gamma =
    [[-6250.     0.     0.     0.     0.     0.]
     [    0. -6250.     0.     0.     0.     0.]
     [    0.     0. -6250.     0.     0.     0.]
     [    0.     0.     0. -6250.     0.     0.]
     [    0.     0.     0.     0. -6250.     0.]
     [    0.     0.     0.     0.     0. -6250.]],
    and Gamma_tildeT =
    [[1. 0. 0. 0. 0. 0.]
     [0. 1. 0. 0. 0. 0.]
     [0. 0. 1. 0. 0. 0.]
     [0. 0. 0. 1. 0. 0.]
     [0. 0. 0. 0. 1. 0.]
     [0. 0. 0. 0. 0. 1.]] 

    The Digital Control is parameterized as:
    T = 8e-05,
    M = 6, and next update at
    t = 8e-05




.. GENERATED FROM PYTHON SOURCE LINES 62-69

Creating a Placehold Control Signal
-----------------------------------

We could, of course, simulate the analog system and digital control above
for a given analog signal. However, this might not always be the use case;
instead, imagine we have acquired such a control signal from a previous
simulation or possibly obtained it from a hardware implementation.

.. GENERATED FROM PYTHON SOURCE LINES 69-94

.. code-block:: default
   :lineno-start: 70


    # In principle, we can create a dummy generator by just


    def dummy_control_sequence_signal():
        while(True):
            yield np.zeros(M, dtype=np.int8)
    # and then pass dummy_control_sequence_signal as the control_sequence
    # to the digital estimator.


    # Another way would be to use a random control signal. Such a generator
    # is already provided in the :func:`cbadc.utilities.random_control_signal`
    # function. Subsequently, a random (random 1-0 valued M tuples) control signal
    # of length

    sequence_length = 10

    # can conveniently be created as

    control_signal_sequences = random_control_signal(
        M, stop_after_number_of_iterations=sequence_length, random_seed=42)

    # where random_seed and stop_after_number_of_iterations are fully optional








.. GENERATED FROM PYTHON SOURCE LINES 95-103

Setting up the Filter
------------------------------------

To produce estimates we need to compute the filter coefficients of the
digital estimator. This is part of the instantiation process of the
DigitalEstimator class. However, these computations require us to
specify both the analog system, the digital control and the filter parameters
such as eta2, the batch size K1, and possible the lookahead K2.

.. GENERATED FROM PYTHON SOURCE LINES 103-122

.. code-block:: default
   :lineno-start: 104


    # Set the bandwidth of the estimator

    eta2 = 1e7

    # Set the batch size

    K1 = sequence_length

    # Instantiate the digital estimator (this is where the filter coefficients are
    # computed).

    digital_estimator = DigitalEstimator(analog_system, digital_control, eta2, K1)

    print(digital_estimator, "\n")

    # Set control signal iterator
    digital_estimator(control_signal_sequences)





.. rst-class:: sphx-glr-script-out

 Out:

 .. code-block:: none

    Digital estimator is parameterized as
        
    eta2 = 10000000.00, 70 [dB],
        
    Ts = 8e-05,
    K1 = 10,
    K2 = 0,
        
    and
    number_of_iterations = 9223372036854775808
        
    Resulting in the filter coefficients
    Af = 
    [[ 9.95009873e-01 -1.07214558e-05 -3.29769511e-05 -7.22193743e-05
      -9.99838614e-05 -6.08602482e-05]
     [ 4.97480948e-01  9.94895332e-01 -3.94810856e-04 -9.35645249e-04
      -1.40157552e-03 -9.46223367e-04]
     [ 1.24240233e-01  4.96834695e-01  9.92598214e-01 -6.11667095e-03
      -9.88175184e-03 -7.42125776e-03]
     [ 2.02574876e-02  1.21940699e-01  4.88233723e-01  9.69889327e-01
      -4.41464933e-02 -3.76124321e-02]
     [ 1.56648671e-03  1.51890153e-02  1.01921548e-01  4.31504641e-01
       8.65342522e-01 -1.31863329e-01]
     [-8.48190802e-04 -3.79206318e-03 -7.66097787e-03  2.91476932e-02
       2.70050483e-01  6.77163594e-01]],
        
    Ab = 
    [[ 1.00500883e+00  1.54861694e-05 -4.74794350e-05  1.01153964e-04
      -1.31857374e-04  7.07416177e-05]
     [-5.02468993e-01  1.00483987e+00  5.74426547e-04 -1.31763025e-03
       1.85555402e-03 -1.11093774e-03]
     [ 1.25425546e-01 -5.01522275e-01  1.00153543e+00  8.50959779e-03
      -1.29342792e-02  8.68475153e-03]
     [-2.02614680e-02  1.22167377e-01 -4.89583646e-01  9.71177642e-01
       5.61398373e-02 -4.32879422e-02]
     [ 1.23757454e-03 -1.35504621e-02  9.62247113e-02 -4.18716306e-01
       8.48271033e-01  1.47273048e-01]
     [ 1.06969462e-03 -4.99244970e-03  1.24120658e-02  1.62939979e-02
      -2.49365903e-01  6.64066057e-01]],
        
    Bf = 
    [[-4.98751645e-01  2.01435011e-06  6.82590295e-06  1.63194985e-05
       2.47281476e-05  1.69487071e-05]
     [-1.24580150e-01 -4.98730814e-01  8.00612785e-05  2.08594140e-04
       3.43169808e-04  2.60386347e-04]
     [-2.07347413e-02 -1.24465299e-01 -4.98271350e-01  1.34555417e-03
       2.39438164e-03  2.01951875e-03]
     [-2.52435229e-03 -2.03346523e-02 -1.22773188e-01 -4.93311312e-01
       1.05608518e-02  1.01139883e-02]
     [-1.12872327e-04 -1.66317069e-03 -1.64790291e-02 -1.10609043e-01
      -4.68327424e-01  3.49448581e-02]
     [ 1.30405025e-04  7.66632154e-04  2.57282644e-03 -1.49723174e-03
      -7.33995907e-02 -4.16260014e-01]],
        
    Bb = 
    [[ 5.01251476e-01  2.90629180e-06 -9.87489414e-06  2.30342675e-05
      -3.29086754e-05  2.00065004e-05]
     [-1.25411625e-01  5.01220654e-01  1.17271246e-04 -2.96315348e-04
       4.58582587e-04 -3.09815586e-04]
     [ 2.08811767e-02 -1.25242491e-01  5.00554230e-01  1.88944089e-03
      -3.16355021e-03  2.39004868e-03]
     [-2.51484999e-03  2.03105319e-02 -1.22872140e-01  4.93854504e-01
       1.35533096e-02 -1.17435470e-02]
     [ 6.36212541e-05 -1.36595554e-03  1.52653250e-02 -1.07513725e-01
       4.64169939e-01  3.92569729e-02]
     [ 1.61551740e-04 -9.68267461e-04  3.49710767e-03 -1.35278958e-03
      -6.81691898e-02  4.12601756e-01]],
        
    and WT = 
    [[ 8.45373598e-02  8.45372372e-04 -2.13025722e-03 -6.40572458e-05
       1.06842223e-04  5.03895749e-06]]. 





.. GENERATED FROM PYTHON SOURCE LINES 123-127

Producing Estimates
-------------------

At this point, we can produce estimates by simply calling the iterator

.. GENERATED FROM PYTHON SOURCE LINES 127-132

.. code-block:: default
   :lineno-start: 128


    for i in digital_estimator:
        print(i)






.. rst-class:: sphx-glr-script-out

 Out:

 .. code-block:: none

    [-0.19527123]
    [-0.19322569]
    [-0.18982144]
    [-0.18509899]
    [-0.17911667]
    [-0.17194968]
    [-0.16368875]
    [-0.15443858]
    [-0.144316]
    [-0.13344799]




.. GENERATED FROM PYTHON SOURCE LINES 133-137

Batch Size and Lookahead
------------------------

Note that batch and lookahead sizes are automatically handled such that for

.. GENERATED FROM PYTHON SOURCE LINES 137-154

.. code-block:: default
   :lineno-start: 137

    K1 = 5
    K2 = 1
    sequence_length = 11
    control_signal_sequences = random_control_signal(
        M, stop_after_number_of_iterations=sequence_length, random_seed=42)
    digital_estimator = DigitalEstimator(
        analog_system, digital_control, eta2, K1, K2)

    # Set control signal iterator
    digital_estimator(control_signal_sequences)

    # The iterator is still called the same way.
    for i in digital_estimator:
        print(i)
    # However, this time this iterator involves computing two batches each
    # involving a lookahead of size one.





.. rst-class:: sphx-glr-script-out

 Out:

 .. code-block:: none

    [-0.24974734]
    [-0.25252069]
    [-0.25370925]
    [-0.25329868]
    [-0.25129497]
    [-0.1377449]
    [-0.12783698]
    [-0.11712884]
    [-0.10575524]
    [-0.09385866]




.. GENERATED FROM PYTHON SOURCE LINES 155-166

Loading Control Signal from File
--------------------------------

Next, we will load an actual control signal to demonstrate the digital
estimator's capabilities. To this end, we will use the
`sinusodial_simulation.adc` file that was produced in
:doc:`./plot_b_simulate_a_control_bounded_adc`.

The control signal file is encoded as raw binary data so to unpack it
correctly we will use the :func:`cbadc.utilities.read_byte_stream_from_file`
and :func:`cbadc.utilities.byte_stream_2_control_signal` functions.

.. GENERATED FROM PYTHON SOURCE LINES 166-170

.. code-block:: default
   :lineno-start: 167


    byte_stream = read_byte_stream_from_file('sinusodial_simulation.adc', M)
    control_signal_sequences = byte_stream_2_control_signal(byte_stream, M)








.. GENERATED FROM PYTHON SOURCE LINES 171-177

Estimating the input
--------------------

Fortunately, we used the same
analog system and digital controls as in this example so


.. GENERATED FROM PYTHON SOURCE LINES 177-204

.. code-block:: default
   :lineno-start: 178


    stop_after_number_of_iterations = 1 << 17
    u_hat = np.zeros(stop_after_number_of_iterations)
    K1 = 1 << 10
    K2 = 1 << 11
    digital_estimator = DigitalEstimator(
        analog_system, digital_control,
        eta2,
        K1,
        K2,
        stop_after_number_of_iterations=stop_after_number_of_iterations
    )
    # Set control signal iterator
    digital_estimator(control_signal_sequences)
    for index, u_hat_temp in enumerate(digital_estimator):
        u_hat[index] = u_hat_temp

    t = np.arange(u_hat.size)
    plt.plot(t, u_hat)
    plt.xlabel('$t / T$')
    plt.ylabel('$\hat{u}(t)$')
    plt.title("Estimated input signal")
    plt.grid()
    plt.xlim((0, 1500))
    plt.ylim((-1, 1))
    plt.tight_layout()




.. image:: /auto_examples/a_getting_started/images/sphx_glr_plot_c_digital_estimator_001.png
    :alt: Estimated input signal
    :class: sphx-glr-single-img





.. GENERATED FROM PYTHON SOURCE LINES 205-210

Plotting the PSD
----------------

As is typical for delta-sigma modulators, we often visualize the performance
of the estimate by plotting the power spectral density (PSD).

.. GENERATED FROM PYTHON SOURCE LINES 210-219

.. code-block:: default
   :lineno-start: 211


    f, psd = compute_power_spectral_density(u_hat[K2:])
    plt.figure()
    plt.semilogx(f, 10 * np.log10(psd))
    plt.xlabel('frequency [Hz]')
    plt.ylabel('$ \mathrm{V}^2 \, / \, \mathrm{Hz}$')
    plt.xlim((f[1], f[-1]))
    plt.grid(which='both')




.. image:: /auto_examples/a_getting_started/images/sphx_glr_plot_c_digital_estimator_002.png
    :alt: plot c digital estimator
    :class: sphx-glr-single-img






.. rst-class:: sphx-glr-timing

   **Total running time of the script:** ( 0 minutes  16.352 seconds)


.. _sphx_glr_download_auto_examples_a_getting_started_plot_c_digital_estimator.py:


.. only :: html

 .. container:: sphx-glr-footer
    :class: sphx-glr-footer-example



  .. container:: sphx-glr-download sphx-glr-download-python

     :download:`Download Python source code: plot_c_digital_estimator.py <plot_c_digital_estimator.py>`



  .. container:: sphx-glr-download sphx-glr-download-jupyter

     :download:`Download Jupyter notebook: plot_c_digital_estimator.ipynb <plot_c_digital_estimator.ipynb>`


.. only:: html

 .. rst-class:: sphx-glr-signature

    `Gallery generated by Sphinx-Gallery <https://sphinx-gallery.github.io>`_
