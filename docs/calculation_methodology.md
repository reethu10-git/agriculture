# Agricultural Calculation Methodology: FAO-56 & Paddy Water Balance

## 1. FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_o$)

The reference evapotranspiration ($ET_o$) defines the rate of evapotranspiration from a hypothetical reference surface of well-watered green grass cover with an assumed height of 0.12 m, a surface resistance of $70\text{ s m}^{-1}$, and an albedo of 0.23.

### Governing Equation
$$ET_o = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

Where:
- $ET_o$: Reference evapotranspiration [$\text{mm day}^{-1}$]
- $R_n$: Net radiation at the crop surface [$\text{MJ m}^{-2}\text{ day}^{-1}$]
- $G$: Soil heat flux density [$\text{MJ m}^{-2}\text{ day}^{-1}$] (assumed $\approx 0$ for daily periods)
- $T$: Mean daily air temperature at 2 m height [$^\circ\text{C}$]
- $u_2$: Wind speed at 2 m height [$\text{m s}^{-1}$]
- $e_s$: Saturation vapour pressure [$\text{kPa}$]
- $e_a$: Actual vapour pressure [$\text{kPa}$]
- $e_s - e_a$: Vapour pressure deficit [$\text{kPa}$]
- $\Delta$: Slope of saturation vapour pressure curve [$\text{kPa }^\circ\text{C}^{-1}$]
- $\gamma$: Psychrometric constant [$\text{kPa }^\circ\text{C}^{-1}$]

---

## 2. Atmospheric & Solar Radiation Derivations

### A. Atmospheric Pressure ($P$) & Psychrometric Constant ($\gamma$)
$$P = 101.3 \left( \frac{293 - 0.0065 z}{293} \right)^{5.26}$$
$$\gamma = 0.000665 P$$
Where $z$ is elevation above sea level in meters ($411\text{ m}$ for Coimbatore).

### B. Saturation and Actual Vapour Pressure
$$e^0(T) = 0.6108 \exp\left( \frac{17.27 T}{T + 237.3} \right)$$
$$e_s = \frac{e^0(T_{max}) + e^0(T_{min})}{2}$$
$$e_a = \frac{e^0(T_{min}) \frac{RH_{max}}{100} + e^0(T_{max}) \frac{RH_{min}}{100}}{2}$$
Slope of saturation vapour pressure curve:
$$\Delta = \frac{4098 [0.6108 \exp(\frac{17.27 T_{mean}}{T_{mean} + 237.3})]}{(T_{mean} + 237.3)^2}$$

### C. Solar Declination & Extraterrestrial Radiation ($R_a$)
For Julian day $J$:
$$d_r = 1 + 0.033 \cos\left( \frac{2\pi J}{365} \right)$$
$$\delta = 0.409 \sin\left( \frac{2\pi J}{365} - 1.39 \right)$$
$$\omega_s = \arccos(-\tan \phi \tan \delta)$$
$$R_a = \frac{24(60)}{\pi} G_{sc} d_r [\omega_s \sin \phi \sin \delta + \cos \phi \cos \delta \sin \omega_s]$$
Where $G_{sc} = 0.0820\text{ MJ m}^{-2}\text{ min}^{-1}$, and $\phi$ is latitude in radians.

### D. Net Radiation ($R_n$)
$$R_{so} = (0.75 + 2 \times 10^{-5} z) R_a$$
$$R_{ns} = (1 - 0.23) R_s = 0.77 R_s$$
$$R_{nl} = \sigma \left[ \frac{T_{max, K}^4 + T_{min, K}^4}{2} \right] (0.34 - 0.14 \sqrt{e_a}) \left( 1.35 \frac{R_s}{R_{so}} - 0.35 \right)$$
$$R_n = R_{ns} - R_{nl}$$

---

## 3. Crop Evapotranspiration ($ET_c$)
$$ET_c = K_c \times ET_o$$
Where $K_c$ represents the crop coefficient according to the phonological stage:
- Rice: Initial = 1.05, Development = 1.15, Mid-Season = 1.25, Late-Season = 0.90.

---

## 4. Effective Rainfall ($P_{eff}$) Formulation

### A. Upland Crops: USDA-SCS Formula
$$P_{eff} = P \times \frac{125 - 0.2 P}{125} \quad \text{for } P \le 250\text{ mm}$$
Small events ($P < 3\text{ mm}$) evaporate from foliage before soil penetration ($P_{eff} = 0$).

### B. Lowland Paddy Rice: Bund Freeboard Storage Model
Rice fields are surrounded by earthen bunds (typically 75–100 mm height). The available bund freeboard storage on day $t$ is:
$$Storage_{avail} = H_{bund} - W_{pond, t-1}$$
Therefore:
$$P_{eff} = \min(P, Storage_{avail})$$
$$Runoff = \max(0, P - Storage_{avail})$$
This physically accurate method avoids the massive errors of treating rainfall in rice like upland crops.

---

## 5. Soil-Water Balance & Alternate Wetting and Drying (AWD)

### Lowland Rice Water Balance
$$W_{pond, t} = W_{pond, t-1} + P_{eff, t} + I_t - ETc_t - Perc_t$$
Where:
- $W_{pond}$: Standing water depth [mm]
- $Perc$: Deep percolation through puddled soil layer [1.5 – 3.0 mm/day]
- $I_t$: Irrigation applied [mm]

**Irrigation Rule (AWD)**:
- Safe AWD allows water to subside to $0\text{ mm}$ (soil surface saturation) during vegetative stages before reapplying $40\text{ mm}$.
- During critical reproductive stage (Panicle Initiation to Flowering), water stress causes floret sterility; thus, a continuous water depth of $30\text{–}50\text{ mm}$ is strictly preserved.
- When $W_{pond} + P_{eff} - ETc - Perc < \text{Threshold}$, irrigation $I_t = Target - W_{pond, projected}$ is scheduled.
