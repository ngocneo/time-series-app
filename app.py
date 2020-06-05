from flask import Flask, flash, render_template, url_for, request, redirect
from ts_functions import TimeSeriesPredictions, TimeSeriesGraphs
from ts_functions import clear_old_files
import os
from werkzeug.utils import secure_filename
from datetime import date, timedelta
import pandas as pd
import numpy as np
from statsmodels.tsa.arima_process import arma_generate_sample


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/files"
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

glossary_data = pd.read_csv("static/glossary.csv").sort_values(by="title")
glossary_data.reset_index(drop=True, inplace=True)

frequencies = {
    "D": "Days",
    "B": "Business days",
    "w": "Weeks",
    "M": "Months",
    "Q": "Quarters",
    "Y": "Years",
}


def allowed_file(filename):
    """
    Checks whether a file's extension is supported/allowed.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/glossary")
def glossary():
    return render_template("glossary.html", definitions=glossary_data)


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        try:
            file = request.files["file"]
            # if user hasn't selected a file, browsers usually submit an empty
            # part ('')
            if file.filename == "":
                flash("No selected file")
                return redirect(request.url)
            # processing filename and saving file
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                clear_old_files("csv")  # removing outdated uploads
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                return redirect(url_for("process_file", filename=filename))
        except (RuntimeError):
            pass
    return render_template("upload.html")


@app.route("/processing_<filename>", methods=["GET", "POST"])
def process_file(filename):
    # importing data from uploaded file
    try:
        data = pd.read_csv("static/files/" + filename, index_col=0)
        data = data.iloc[:, -1]  # selecting last column for analysis
        data.index = pd.to_datetime(data.index)
        if len(data) <= 21:  # avoiding errors due to very small samples
            return redirect(url_for("upload_file"))
    except (ValueError):  # raised if file isn't standard CSV
        clear_old_files("csv")  # removing the bad uploaded file
        return redirect(url_for("upload_file"))
    clear_old_files("png")  # removing outdated graphs
    predictions = TimeSeriesPredictions(data)  # fitting  models
    results = predictions.results
    sample = predictions.sample
    totals = sample.sum().round(2).to_numpy()
    plots = TimeSeriesGraphs(data, results)
    graphs = {
        "acf&pacf": plots.acf_pacf,
        "lineplot": plots.lineplot,
        "model_fit": plots.modelfit,
        "seasonal_decomposition": plots.seasonal_decomposition,
    }

    return render_template(
        "processing_file.html",
        graphs=graphs,
        filename=filename,
        sample=sample,
        totals=totals,
    )


@app.route("/sample", methods=["GET", "POST"])
def create_sample():
    today = date.today().isoformat()
    month_later = (date.today() + timedelta(days=30)).isoformat()
    if request.method == "POST":
        try:
            # collecting parameters from form
            start = request.form["start_date"]
            stop = request.form["end_date"]
            frequency = request.form["frequency"]
            ar_order = int(request.form["ar_order"])
            ma_order = int(request.form["ma_order"])
        except KeyError:
            start, stop = today, month_later
            frequency, ar_order, ma_order = "D", 1, 1

        try:
            # creating user-defined ARMA sample
            index = pd.date_range(start, stop, freq=frequency)
            size = len(index)
            np.random.seed(123)
            ar = np.linspace(-0.9, 0.9, ar_order)
            ma = np.linspace(-1, 1, ma_order)
            y = arma_generate_sample(
                ar, ma, size, scale=100, distrvs=np.random.standard_normal
            )
            data = pd.Series(y, index=index, name="Sample")
            clear_old_files("png")  # removing old graphs
            predictions = TimeSeriesPredictions(data)  # fitting  models
            results = predictions.results
            sample = predictions.sample
            totals = sample.sum().round(2).to_numpy()
            plot = TimeSeriesGraphs(data, results)
            graphs = {
                "acf&pacf": plot.acf_pacf,
                "lineplot": plot.lineplot,
                "model_fit": plot.modelfit,
                "seasonal_decomposition": plot.seasonal_decomposition,
            }
            return render_template(
                "processing_file.html",
                graphs=graphs,
                filename="Sample",
                sample=sample,
                totals=totals,
            )
        except (ValueError):  # due to small sample size
            input_error = "Please try again... Generated sample too small."
        except ZeroDivisionError:  # raised when sample size=21, thus Autoreg
            # function, set up here with lag up to 10 has only 1 viable step.
            input_error = "Please increase sample size."

        return render_template(
            "processing_sample.html",
            frequencies=frequencies,
            today=today,
            month_later=month_later,
            input_error=input_error,
        )

    return render_template(
        "processing_sample.html",
        sample=True,
        frequencies=frequencies,
        today=today,
        month_later=month_later,
    )


if __name__ == "__main__":
    app.run()
