# -*- coding: utf-8 -*-
"""
Created on Tue Mar  2 11:25:34 2023

@author: N. Miguens
"""

import pandas as pd
from matplotlib import pyplot as plt
from sklearn.linear_model import LinearRegression
import warnings 
import statsmodels.formula.api as smf

import numpy as np 


class Regression():
    def __init__(self, points : pd.DataFrame, dv : float = 0.3, n_max : int = 2) -> None:
        # Ensemble des points nettoyés 
        self.points = points.copy()
        self.high_intensity_points = pd.DataFrame()

        # Paramètres de la méthode 
        self.dv = dv # Petit interval de vitesse
        self.n_max = n_max # Nombre de points à sélectionner par interval de vitesse dv

        # Sportifs dans les données
        self.players = points.Player.unique()

        # Régressions par sportif
        self.players_linear_regression = pd.DataFrame()
        self.players_quantile_regression = pd.DataFrame()

    def intensity_max_identification(self) -> pd.DataFrame:
        """Identification des points à maximum intensité selon la méthode de JB Morin"""
        # ID des intervals dv
        self.points.loc[:, "dv"] = self.points.Speed // self.dv
        # Plus grandes valeurs d'accélération par interval
        self.points.loc[:, "rank_Acceleration_dv"] = self.points.groupby(['Player', 'dv']).Acceleration.rank(method = 'dense', ascending = False)
        # Points à intensité maximal
        high_intensity_points = self.points[self.points.rank_Acceleration_dv <= self.n_max]

        # LE point à intensité maximal
        high_intensity_points.loc[:, "max_Acceleration"] = high_intensity_points.groupby(['Player']).Acceleration.transform('max')
        max_Speed_at_max_Acceleration = high_intensity_points.query('Acceleration == max_Acceleration').groupby(['Player']).Speed.max()
        max_Speed_at_max_Acceleration = pd.DataFrame(max_Speed_at_max_Acceleration.values, columns = ['max_Speed_at_max_Acceleration'], index = max_Speed_at_max_Acceleration.index)

        # La regression se fera uniquement sur les points de vitesse supérieur à ce dernier point
        high_intensity_points = high_intensity_points.merge(max_Speed_at_max_Acceleration, on = 'Player')
        high_intensity_points = high_intensity_points.query('Speed >= max_Speed_at_max_Acceleration')
        self.high_intensity_points = high_intensity_points.copy()
        return high_intensity_points
    
    def regression_lineaire(self):
        """Calcul de la régression linéaire sur les points à haute intensité"""
        # Calcul des régressions linéaires sportif par sportif
        self.players_linear_regression = pd.DataFrame(self.high_intensity_points.groupby('Player').apply(self.group_linear_regression), columns = ['linear_regression'])

        # Valeurs intéressantes
        # Calcul de a0 et s0 selon les valeurs de la regression lineaire
        self.players_linear_regression.loc[:, "a0 : Regression linéaire"] = self.players_linear_regression.linear_regression.apply(lambda x : x.intercept_[0])
        self.players_linear_regression.loc[:, "s0 : Regression linéaire"] = self.players_linear_regression.linear_regression.apply(lambda x : - x.intercept_[0] / x.coef_[0,0])

        self.players_linear_regression = self.players_linear_regression.drop(columns = ['linear_regression'])
        return self.players_linear_regression
    
    def group_linear_regression(self, df):
        """Régression linéaire à exécuter dans un groupby"""
        y = df[['Acceleration']]
        X = df[['Speed']]
        linear_regression = LinearRegression().fit(X, y)
        if linear_regression.score(X, y) <= 0.5 :
            player = df.Player.unique()[0]
            warnings.warn(f"La regression linéaire du joueur {player} n'est pas de qualité. Veuillez vérifier les données")
            return LinearRegression()
        return linear_regression
    
    def plot_linear(self, file_name : str, display : bool = False):
        """Créer un visuel de la régression lineaire."""
        for player in self.players :

            player_points = self.points[self.points.Player == player]
            player_high_intensity = self.high_intensity_points[self.high_intensity_points.Player == player]
            player_regression = self.players_linear_regression.loc[player, :]

            # Nouvelle figure
            plt.figure()
        
            # Plot des données brutes
            plt.scatter(player_points.Speed, player_points.Acceleration, alpha = 0.5, s = 20)
            
            # Points en rouge les points à haute intensité
            if not player_high_intensity.empty :
                plt.scatter(player_high_intensity.Speed, player_high_intensity.Acceleration, alpha = 1, s = 20, c = "red")
            else : 
                raise ValueError("Des points à haute intensité doivent être identifiés.")
            
            # Point vert pour la valeur de puissance maximale liberée
            Amax = player_high_intensity.max_Acceleration.iloc[0]
            Vmax = player_high_intensity.max_Speed_at_max_Acceleration.iloc[0]
            plt.scatter(Vmax, Amax, alpha = 1, s = 50, c = "green")

            # Trace droite
            s0 = player_regression[["s0 : Regression linéaire"]].iloc[0]
            a0 = player_regression[["a0 : Regression linéaire"]].iloc[0]
            droite = np.array([[0,s0], [a0, 0]], dtype = object)
            plt.plot(droite[0], droite[1], color='red')
            # Ecriture des valeurs s0 et a0
            plt.figtext(0.3, 0.8, f'a0 = {a0:.2f} m/s²', ha="center", color = 'red', fontsize=10, bbox={"facecolor":"white", "alpha":0.5, "pad":5})
            plt.figtext(0.8, 0.4, f's0 = {s0:.2f} m/s', ha="center", color = 'red', fontsize=10, bbox={"facecolor":"white", "alpha":0.5, "pad":5})
    
            # Axes et titre du graph
            plt.xlabel('Speed (m/s)')
            plt.ylabel('Acceleration (m/s²)')
            plt.xlim([0,11])
            plt.ylim([0,11])
            plt.title(f"Régression linéaire : {player}")
            plt.savefig(f"./results/images/{file_name + '_' + player}_Linear_Regression.png")
            if display :
                plt.show()   
    
    def regression_quantile(self):
        """Calcul de régressions quantiles sur les points à haute intensité"""
        # Calcul des régressions linéaires sportif par sportif
        self.players_quantile_regression = self.high_intensity_points.groupby('Player').apply(self.group_quantile_regression)
        return self.players_quantile_regression 
        
    def group_quantile_regression(self, df):
        """Régression quantile à exécuter dans un groupby"""
        model = smf.quantreg('Acceleration ~ Speed', df[['Speed', 'Acceleration']].astype(float))
        quantiles = np.arange(.05, .96, .01)
        models = pd.DataFrame([self.model_fit(q, model) for q in quantiles], columns=['q', 'a0', 'b'])
        models.loc[:, "s0"] = - models.a0 / models.b
        return models[['q', 'a0', 's0']]
    
    def model_fit(self, q, model):
        results = model.fit(q = q)
        return q, results.params['Intercept'], results.params['Speed']
    
    def compute_quantile_a0_s0(self):
        # Valeurs intéressantes
        # Calcul de a0 et s0 selon les valeurs de la regression quantile
        df_a0 = self.players_quantile_regression.groupby(['Player']).a0.agg({'mean', 'std'}).rename(columns = {'mean' : 'a0 : Regression quantile', 'std' : 'std_a0'})
        df_s0 = self.players_quantile_regression.groupby(['Player']).s0.agg({'mean', 'std'}).rename(columns = {'mean' : 's0 : Regression quantile', 'std' : 'std_s0'})
        return pd.concat([df_a0, df_s0], axis = 1)
    
    def plot_quantile(self, file_name : str, display : bool = False):
        """Créer un visuel de la régression lineaire."""
        for player in self.players :

            player_points = self.points[self.points.Player == player]
            player_high_intensity = self.high_intensity_points[self.high_intensity_points.Player == player]
            player_quantile_all = self.players_quantile_regression.loc[player, :]
            player_quantile = self.compute_quantile_a0_s0().loc[player, :]

            # Nouvelle figure
            plt.figure()
        
            # Plot des données brutes
            plt.scatter(player_points.Speed, player_points.Acceleration, alpha = 0.5, s = 20)
            
            # Points en rouge les points à haute intensité
            if not player_high_intensity.empty :
                plt.scatter(player_high_intensity.Speed, player_high_intensity.Acceleration, alpha = 1, s = 20, c = "red")
            else : 
                raise ValueError("Des points à haute intensité doivent être identifiés.")
            
            # Point vert pour la valeur de puissance maximale liberée
            Amax = player_high_intensity.max_Acceleration.iloc[0]
            Vmax = player_high_intensity.max_Speed_at_max_Acceleration.iloc[0]
            plt.scatter(Vmax, Amax, alpha = 1, s = 50, c = "green")

            # Trace multiples droites
            for q in np.arange(.05, .96, .1):
                # Trace droite
                s0 = player_quantile_all.loc[player_quantile_all.q == q, 's0']
                a0 = player_quantile_all.loc[player_quantile_all.q == q, 'a0']
                droite = np.array([[0,s0], [a0, 0]], dtype = object)
                plt.plot(droite[0], droite[1], linestyle='dotted', color='grey')

            # Trace droite
            s0 = player_quantile[["s0 : Regression quantile"]].iloc[0]
            a0 = player_quantile[["a0 : Regression quantile"]].iloc[0]
            std_s0 = player_quantile[["std_s0"]].iloc[0]
            std_a0 = player_quantile[["std_a0"]].iloc[0]

            droite = np.array([[0,s0], [a0, 0]], dtype = object)
            plt.plot(droite[0], droite[1], color='red')
            # Ecriture des valeurs s0 et a0
            plt.figtext(0.3, 0.8, f'a0 = {a0:.2f} ± {std_a0:.2f} m/s² ', ha="center", color = 'red', fontsize=10, bbox={"facecolor":"white", "alpha":0.5, "pad":5})
            plt.figtext(0.8, 0.4, f's0 = {s0:.2f} ± {std_s0:.2f} m/s', ha="center", color = 'red', fontsize=10, bbox={"facecolor":"white", "alpha":0.5, "pad":5})

            # Axes et titre du graph
            plt.xlabel('Speed (m/s)')
            plt.ylabel('Acceleration (m/s²)')
            plt.xlim([0,11])
            plt.ylim([0,11])
            plt.title(f"Acceleration - Speed Profil : {player}")
            plt.savefig(f"./results/images/{file_name + '_' + player}_Quantile_Regression.png")
            if display :
                plt.show()   

    def save(self, file_name : str):
        """Écrit les résultats des régressions dans un dataframe"""
        if self.players_linear_regression.empty and self.players_quantile_regression.empty : 
            raise ValueError("Aucune méthode de calcul de profil accélération-vitesse n'a été faite.")
        
        elif self.players_linear_regression.empty :
            self.compute_quantile_a0_s0().to_csv(f"./results/ProfilAV_insitu_{file_name}.csv")

        elif self.players_quantile_regression.empty : 
            self.players_linear_regression.to_csv(f"./results/ProfilAV_insitu_{file_name}.csv")
        else :
            pd.concat([self.players_linear_regression, self.compute_quantile_a0_s0()], axis = 1).to_csv(f"./results/ProfilAV_insitu_{file_name}.csv")
