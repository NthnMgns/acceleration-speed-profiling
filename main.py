#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  3 14:34:15 2023

@author: N Miguens
"""
import sys
import os
sys.path.insert(0, os.getcwd() + '/code')

from datetime import datetime
from code.outliers import Outliers
from code.regression import Regression
import pandas as pd
from matplotlib import pyplot as plt


nom_fichier = '...'
display = False

###################################################################################
# -------------------- Import et trasnformation d'un fichier -------------------- #
###################################################################################

df_seance = pd.read_csv(f"data/{nom_fichier}.csv", parse_dates=['formatted local time'], sep = ';')

# Transformation du fichier pour qu'il réponde au format attendu.
df_seance = df_seance.rename(columns = {'formatted local time' : 'Heure', 'full name' : 'Player', 'speed in m/s' : 'speed', 'acceleration in m/s2' : 'accel'})
df_seance = df_seance.dropna(subset=['accel', 'speed'])

# Conversion en type numérique
try : 
    df_seance.loc[:, 'speed'] = pd.to_numeric(df_seance.speed) 
    df_seance.loc[:, 'accel'] = pd.to_numeric(df_seance.accel)
except : 
    df_seance.loc[:, 'speed'] = pd.to_numeric(df_seance.speed.str.replace(',', '.').astype(float))
    df_seance.loc[:, 'accel'] = pd.to_numeric(df_seance.accel.str.replace(',', '.').astype(float))

# La date est nécessaire pour la suite
df_seance.loc[:, 'Date'] = df_seance.Heure.dt.date
# Si calcul de l'accélération il est nécessaire d'ordonner le fichier
df_seance = df_seance.sort_values(by = ['Player', 'Heure'])

# Recalcul de l'accélération ? 
# - Kinexon LPS : Qualité suffisante de l'accélération 
# - GPS Catapult : Résultats de l'IMU nécessite un recalcul de l'accélération
#df_seance["accel"] = (df_seance.speed - df_seance.speed.shift(1))/((df_seance.Heure - df_seance.Heure.shift(1)).dt.total_seconds())

###################################################################################
# ------------------------------- Quelques tests -------------------------------- #
###################################################################################

for column in ['Date', 'speed', 'accel', 'Player', 'Heure'] :
    assert column in df_seance.columns.tolist(), "Des colonnes essentielles au déroullement du code sont manquantes."
assert df_seance.speed.quantile(0.99) <= 10, "Les données de vitesse sont probablement en km/h. Merci de les convertir en m/s."

###################################################################################
# -------------------- Profil Accélération Vitesse In Situ -------------------- #
###################################################################################

# Outliers
outliers = Outliers(df_seance)
outliers.misuse_error_identification()
outliers.measurement_error_identification()
#outliers.plot(nom_fichier, display=display)

# Régressions - Étape 1
regression = Regression(outliers.correct_points)
regression.intensity_max_identification()

# Régression linéaire classique (JB Morin)
regression.regression_lineaire()
#regression.plot_linear(nom_fichier, display=display)

# Régression quantile (N Miguens)
regression.regression_quantile()
regression.plot_quantile(nom_fichier, display = display)

# On enregistre les résultats 
regression.save(nom_fichier)

