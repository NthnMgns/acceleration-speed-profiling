#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  3 14:34:15 2023

@author: N Miguens
"""
import sys
import os
sys.path.insert(0, os.getcwd() + '/code')

from code.outliers import Outliers
from code.regression import Regression
import pandas as pd
import argparse


if __name__ == "__main__":

    # ---------------------- Parse Arguments ---------------------------- #

    parser = argparse.ArgumentParser(
        prog="Speed-Acceleration Profiling",
        description="Speed-Acceleration Profiling",
        argument_default=False)

    parser.add_argument(
        "-f", "--filename", 
        help="Select a csv file in data folder", 
        type=str)
    
    parser.add_argument('-s','--convert_speed', action="store_true", help="Apply speed conversion from km/h to m/s.")
    parser.add_argument('-k','--keep_acceleration', action="store_true", help="Use acceleration in csv file")
    
    parser.add_argument("--dv", type =float, help="Small speed range in max intensity identification.")
    parser.add_argument("--n_max", type =int, help="Numbers of points by small speed range in max intensity identification.")

    args = parser.parse_args()
    filename, convert_speed, keep_acceleration = args.filename, args.convert_speed, args.keep_acceleration
    dv, n_max = args.dv, args.n_max


    # ---------------------- Default Arguments ---------------------------- #

    sep = ','
    filename = filename if filename else 'Session_example'
    convert_speed = convert_speed if convert_speed else False 
    keep_acceleration = keep_acceleration if keep_acceleration else False

    display = False
    save_plot_outliers = True
    save_plot_linear_regression = False
    save_plot_quantile_regression = True

    dv = dv if dv else 0.3
    n_max = n_max if n_max else 2

    # -------------------- File Loading -------------------- #

    df_session = pd.read_csv(f"data/{filename}.csv", parse_dates=['Timestamp'], sep = sep)
    df_session = df_session.dropna(subset=['Acceleration', 'Speed'])

    # Conversion en type numérique
    try : 
        df_session.loc[:, 'Speed'] = pd.to_numeric(df_session.Speed) 
        df_session.loc[:, 'Acceleration'] = pd.to_numeric(df_session.Acceleration)
    except : 
        df_session.loc[:, 'Speed'] = pd.to_numeric(df_session.Speed.str.replace(',', '.').astype(float))
        df_session.loc[:, 'Acceleration'] = pd.to_numeric(df_session.Acceleration.str.replace(',', '.').astype(float))

    # Km/h to m/s ? 
    if convert_speed :
        df_session.loc[:, 'Speed'] = df_session.Speed / 3.6

    # La date est nécessaire pour la suite
    if not 'Date' in df_session.columns :
        df_session.loc[:, 'Date'] = df_session.Timestamp.dt.date

    # Si calcul de l'accélération il est nécessaire d'ordonner le fichier
    df_session = df_session.sort_values(by = ['Player', 'Timestamp'])

    # Recalcul de l'accélération ? 
    if not keep_acceleration :
        df_session["Acceleration"] = (df_session.Speed - df_session.Speed.shift(1))/((df_session.Timestamp - df_session.Timestamp.shift(1)).dt.total_seconds())


    # ------------------------------- Tests -------------------------------- #

    for column in ['Date', 'Speed', 'Acceleration', 'Player', 'Timestamp'] :
        assert column in df_session.columns.tolist(), "Des colonnes essentielles au déroullement du code sont manquantes."

    assert df_session.Speed.quantile(0.99) <= 10, "Les données de vitesse sont probablement en km/h. Merci de les convertir en m/s."

    # -------------------- In-Situ Speed-Acceleration Profiling -------------------- #
    # Outliers
    outliers = Outliers(df_session)
    outliers.misuse_error_identification()
    outliers.measurement_error_identification()
    if save_plot_outliers :
        outliers.plot(filename, display = display)

    # Régressions - Étape 1
    regression = Regression(outliers.correct_points, dv=dv, n_max=n_max)
    regression.intensity_max_identification()

    # Régression linéaire classique (JB Morin)
    regression.regression_lineaire()
    if save_plot_linear_regression :
        regression.plot_linear(filename, display=display)

    # Régression quantile (N Miguens)
    regression.regression_quantile()
    if save_plot_quantile_regression :
        regression.plot_quantile(filename, display = display)

    # On enregistre les résultats 
    regression.save(filename)

