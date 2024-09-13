# Lecture exercise

```{Note}
This exercise shows some of the basic principles of an LCA. It serves educational purposes and should not be used for guidance in practice. The lecture, which covered this example, was given in the course Sustainable Construction Members in the Master Civil Engineering, track Structural Engineering, by [Henk Jonkers](https://www.tudelft.nl/citg/over-faculteit/afdelingen/materials-mechanics-management-design-3md/sections-labs/materials-environment/staff/prof-dr-hm-henk-jonkers) in the academic year 2023-2024.
```

## Goal
Calculate ECI value for materials (LCA module A1-A3) used for construction and transportation (LCA module A4) and construction processes (LCA module A5) of a concrete water reservoir (thus construction phase only), and determine which input variable (material or process) contributes most to the construction stage ECI value, and give advice on options on how the ECI value can possibly be decreased.

## Data
The necessary materials and processes of the required LCA modules are given in {numref}`inputs`.
```{table} Materials and processes amounts and distances
:name: inputs
| Inputs          | Quantity    | Unit     | Distance | Unit | Required Quantity | Unit      |
|-----------------|-------------|----------|----------|------|-------------------|-----------|
| Concrete        | 7.56E+05    | [kg]     |          |      | 7.56E+05          | [kg]      |
| Steel           | 1.73E+04    | [kg]     |          |      | 1.73E+04          | [kg]      |
| Sand            | 1.20E+05    | [kg]     |          |      | 1.20E+05          | [kg]      |
| Truck mixer     | 3.15E+02    | [m^3]    | 45       | [km] | 1.42E+04          | [m^3*km]  |
| Lorry           | 1.73E+01    | [ton]    | 125      | [km] | 2.17E+03          | [ton*km]  |
| Welding casting | 2.88E+02    | [h]      |          |      | 2.88E+02          | [h]       |
```

The impact categories per materials and process are given in {numref}`impact_categories`.
```{table} Impact categories per material/process
:name: impact_categories
| Inputs          | Unit       | GWP      | HTP      | AP        |
|-----------------|------------|----------|----------|-----------|
| Concrete        | [kg]       | 0.0921   | 0.0102   | 0.0002    |
| Steel           | [kg]       | 1.79     | 3.81     | 0.0074    |
| Sand            | [kg]       | 0.0025   | 0.0017   | 0.0001    |
| Truck mixer     | [m^3*km]   | 0.22     | 0.04     | 0.0013    |
| Lorry           | [ton*km]   | 0.13     | 0.038    | 0.0007    |
| Welding casting | [h]        | 43.3289  | 27.4484  | 0.3335    |
```

Total shadow costs are set to the following per unit of input:
- GWP: € 0.05
- HTP: € 0.09
- AP: € 4.00

## Questions

### 1 What is the total (construction) environmental cost (ECI value) of the concrete water reservoir?
````{admonition} Solution
:class: tip, dropdown
By multiplying the materials and processes data from {numref}`inputs` with {numref}`impact_categories` and its corresponding shadow costs, the costs per material/process can be calculated, displayed in {numref}`costs`.

```{table} Cost per material/process
:name: costs
| Inputs          | Unit       | EUR/input | GWP      | HTP      | AP        |
|-----------------|------------|----------|----------|----------|-----------|
| Concrete        | [kg]       | € 4,780.19 | 0.0921   | 0.0102   | 0.0002    |
| Steel           | [kg]       | € 8,004.15 | 1.79     | 3.81     | 0.0074    |
| Sand            | [kg]       | € 81.36    | 0.0025   | 0.0017   | 0.0001    |
| Truck mixer     | [m^3*km]   | € 280.67   | 0.22     | 0.04     | 0.0013    |
| Lorry           | [ton*km]   | € 27.55    | 0.13     | 0.038    | 0.0007    |
| Welding casting | [h]        | € 1,719.59 | 43.3289  | 27.4484  | 0.3335    |
```

The total costs can now be summed and amount to € 14,893.50. 

````

### 2 Which two inputs (materials or processes) contribute most to the total environmental impact?
```{admonition} Solution
:class: tip, dropdown
Steel the most, concrete 2nd
```

### 3 Suggest two measures which can be taken to lower the impact most effectively?
```{admonition} Solution
:class: tip, dropdown
- Make a more efficient design that creates less tensile forces, thereby requiring less reinforcement steel
- Use another form of concrete, geopolymer concrete
```



