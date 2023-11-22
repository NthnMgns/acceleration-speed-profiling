# -*- coding: utf-8 -*-
"""
Created on Wed Jun  9 16:55:56 2023

@author: N. Miguens 
"""

import pandas as pd
from matplotlib import pyplot as plt
from sklearn.cluster import DBSCAN

# Permet de ne pas afficher les warnings
import warnings
warnings.filterwarnings("ignore")



### -------------------- Variables numeriques ---------------------------- ###
# Distance maximale entre deux points pour les considerer comme voisins
# profil joueur
eps_DBSCAN = 0.5
# profil seance
#eps_DBSCAN = 0.6
# Nombre minimal de voisins pour dire que l'observation est coeur
# profil joueur
# neighb_DBSCAN = 4
# profil seance
neighb_DBSCAN = 3
# Nombre d'outliers minimale pour supprimer une journée entière
nb_outlier = 10



class Outliers():
    """
    Objet identifiant les erreurs de mesure et de mauvaise utilisation.
    Contient les bons points, les erreurs de mesure et erreurs de mauvaise utilisation.
    """
    def __init__(self, points : pd.DataFrame, nb_outlier : int = 10, neighb_DBSCAN : int = 3, eps_DBSCAN : float= 0.5) -> None:
        # Deux types d'erreurs que l'on peut supprimer
        self.measurement_error = pd.DataFrame()
        self.misuse_error = pd.DataFrame()

        # Ensemble des joueurs du dataframe
        self.players = points.Player.unique()

        # Paramètres des méthodes d'identification des erreurs
        self.nb_outlier = nb_outlier
        self.neighb_DBSCAN = neighb_DBSCAN
        self.eps_DBSCAN = eps_DBSCAN

        # Suppression des valeurs négatives (inutiles ici)
        self.correct_points = points[(points.accel >= 0)]

    def misuse_error_identification(self) -> pd.DataFrame :
        """Identification des erreurs de mauvaises utilisations.
        10.93 - 10.93/10.5 * vitesse : mean + 3 * std (cf papier)."""
        # Identification
        outliers = self.correct_points[(self.correct_points.accel >= 0) & (self.correct_points.accel >= 10.93 - 10.93/10.5 * self.correct_points.speed)]
        outliers.loc[:, 'n_error'] = outliers.groupby(['Player', 'Date']).speed.transform('count')
        outliers = outliers[outliers.n_error >= self.nb_outlier]

        # Suppression des outliers dans la base
        outliers_index = outliers.index
        self.correct_points = self.correct_points[~self.correct_points.index.isin(outliers_index)]

        # Sauvegarde de ces points
        self.misuse_error = outliers.copy()
        return outliers

    def measurement_error_identification(self) -> pd.DataFrame :
        """Identification des erreurs de mesure. Le DBSCAN permet d'isoler les points qui sont physiquement trop loin des autres pour correspondre à une trajectoire plausible."""
        # Identification des erreurs de mesures
        # Pour réduire le temps de calcul, on conserve uniquement les points intéressants pour le DBSCAN 
        players_sample = self.correct_points[self.correct_points.accel >= 5 - self.correct_points.speed] 
        
        # Verification si l'échantillon d'intérêt est vide
        if players_sample.empty :
            return pd.DataFrame()
        
        # Detection des outliers grace a une methode de clustering
        players_sample["label"] = players_sample.groupby('Player').apply(self.DBSCAN_clustering).T.values
        outliers_DBSCAN = players_sample[players_sample.label == -1]
    
        # Suppression des outliers dans la base
        outliers_DBSCAN_index = outliers_DBSCAN.index
        self.correct_points = self.correct_points[~self.correct_points.index.isin(outliers_DBSCAN_index)]

        # Sauvegarde de ces points
        self.measurement_error = outliers_DBSCAN.copy()
        return outliers_DBSCAN
    
    def DBSCAN_clustering(self, df : pd.DataFrame):
        """Mise en forme de l'algorithme de DBSCAN pour l'intégrer à un groupby."""
        clustering = DBSCAN(eps=self.eps_DBSCAN, min_samples=self.neighb_DBSCAN).fit(df[["speed", "accel"]])
        return pd.Series(clustering.labels_, index = df.index)

    def plot(self, file_name : str, display : bool = False) -> None:
        """Trace le nuage de points comprenant les deux types d'outliers (noir et rouge) et les données propres (bleu)."""
        for player in self.players :

            player_correct_points = self.correct_points[self.correct_points.Player == player]
            player_measurement_error = self.measurement_error[self.measurement_error.Player == player]
            player_misuse_error = self.misuse_error[self.misuse_error.Player == player]

            # Nouvelle figure
            plt.figure()
        
            # Plot des données brutes avec les outliers detectés
            plt.scatter(player_correct_points.speed, player_correct_points.accel, alpha = 0.5, s = 20)
            
            # Points en rouge pour les outliers d'utilisation
            if not player_measurement_error.empty :
                plt.scatter(player_measurement_error.speed, player_measurement_error.accel, alpha = 1, s = 20, c = "red")
        
            # Points en noir pour les outliers de mesure
            if not player_misuse_error.empty :
                plt.scatter(player_misuse_error.speed, player_misuse_error.accel, alpha = 1, s = 20, c = "black")
                
            plt.xlabel('Vitesse (m/s)')
            plt.ylabel('Accélération (m/s²)')
            plt.xlim([0,11])
            plt.ylim([0,11])
            plt.title(f"Outliers : {player}")
            plt.savefig(f"./results/images/{file_name + '_' + player}_outliers.png")
            if display :
                plt.show()    