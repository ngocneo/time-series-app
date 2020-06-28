import pandas as pd
import numpy as np
from statsmodels.graphics.tsaplots import plot_pacf, plot_acf
import statsmodels.api as sm
import matplotlib.pyplot as plt
from datetime import datetime
from glob import glob
import os
import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["legend.frameon"] = True


def clear_old_files(extension, filepath="static/files/"):
    """
    A utility function to remove old files of {extension} format, from the
    {filepath} folder.
    """
    old_files = glob("".join([filepath, "*.", extension]), recursive=True)
    for file in old_files:
        os.remove(file)


class TimeSeriesPredictions:
    def __init__(self, data):
        self.results = self.fit_tsmodels(data).round(2)
        self.sample = self.results.tail(14)

    def fit_tsmodels(self, data, ratio=0.6) -> pd.DataFrame:
        """
        Fits time series models on the data. Predictions are then returned as
        a dataframe with a column for each fitted model.
        """
        # setting prediction parameters
        n, index = len(data), data.index
        start = index[int(n * (1 - ratio))]
        end = index[-1]

        # Fitting models and making predictions
        model1 = sm.tsa.AutoReg(data, lags=10).fit().predict(start, end)

        try:  # Searching for an appropriate ARMA order
            arma_ic = sm.tsa.arma_order_select_ic(
                data, ic="bic", trend="nc", fit_kw={"dist": 0}
            )
            arma_order = max(arma_ic.bic_min_order, (1, 1))
            model2 = sm.tsa.ARMA(data, arma_order
                                 ).fit(disp=0).predict(start, end)
        except ValueError:
            try:  # Explicitly attempt to fit an ARMA (1,1) model
                model2 = sm.tsa.ARMA(data, (1, 1)
                                     ).fit(disp=0).predict(start, end)
            except ValueError:
                # Contingency in case all ARMA models above fail to converge
                model2 = pd.DataFrame(
                    {"X": [np.nan] * int(n * ratio)},
                    index=pd.date_range("2020-01-01", periods=100),
                )

        model3 = (
            sm.tsa.ExponentialSmoothing(data, trend="add", seasonal="add")
            .fit().predict(start, end)
        )

        # returning results as a dataframe
        models_dict = {"AR": model1, "ARMA": model2,
                       "Exponential Smoothing": model3}
        original = data.loc[start:]
        return pd.DataFrame({'Actual Data': original, **models_dict})


class TimeSeriesGraphs:
    def __init__(self, data, results):
        self.file_folder = "static/files/"
        self.acf_pacf = self.plot_acf_pacf(data)
        self.lineplot = self.plot_line(data)
        self.modelfit = self.plot_model_fit(data, results)
        self.seasonal_decomposition = self.plot_seanonal_decomposition(data)
        self.terminate()

    def plot_acf_pacf(self, data):
        """
        Produces the ACF & PACF graphs, saving them as a png file, and
        returning their location(name).
        """
        fig = plt.figure(figsize=(8, 6))
        ax1, ax2 = fig.add_subplot(211), fig.add_subplot(212)
        plot_acf(data.values, ax=ax1, color="navy")
        plot_pacf(data.values, ax=ax2, color="navy")
        name = self.file_folder + str(datetime.now()) + "_acf_pacf_plots.png"
        plt.savefig(name, transparent=True)

        return name

    def plot_line(self, data):
        """
        Plots the data, saves the graph as a png file, and returns its
        location(name).
        """
        plt.figure(figsize=(8, 4.5))
        plt.plot(data, color="navy")
        plt.xticks(rotation=30)
        plt.title("A line-plot of the data", size=15, pad=10)
        name = self.file_folder + str(datetime.now()) + "_line_plot.png"
        plt.savefig(name, transparent=True)

        return name

    def plot_model_fit(self, data, results):
        """
        Plots the original and predicted values for each time series model
        fitted, saves the graphs as png files, and returns a list of file
        locations(names).
        """
        names = []
        for model, values in results.drop('Actual Data', axis=1).iteritems():
            plt.figure(figsize=(8, 4.5))
            plt.plot(data, label="Original", color="navy")
            plt.plot(values, label="Modelled", color="aqua")
            plt.title(model + " Model Fit", size=15, pad=10)
            plt.xticks(rotation=30)
            name = "".join(
                [self.file_folder, str(datetime.now()), "-", model, ".png"])
            names.append(name)
            plt.savefig(name, transparent=True)

        return names

    def plot_seanonal_decomposition(self, data):
        """
        Performs basic seasonal decomposition, plots the various components,
        saves them as a png file, and returns their location.
        """
        name = "".join(
            [self.file_folder, str(datetime.now()), "_seasonal-decomp.png"])
        sm.tsa.STL(data).fit().plot().autofmt_xdate()
        plt.savefig(name, transparent=True)

        return name

    def terminate(self):
        """Closes all lingering `matplotlib.pyplot` `Figure`s"""

        plt.close("all")
