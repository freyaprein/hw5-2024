import pathlib
from typing import Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class QuestionnaireAnalysis:
    """Reads and analyzes data generated by the questionnaire experiment.
    Should be able to accept strings and pathlib.Path objects.
    """

    def __init__(self, data_fname: Union[pathlib.Path, str]):
        self.data_fname = pathlib.Path(data_fname).resolve()
        if not self.data_fname.exists():
            raise ValueError(f"File {self.data_fname} doesn't exist.")
        self.data = pd.DataFrame()

    def read_data(self):
        """Reads the json data located in self.data_fname into memory, to
        the attribute self.data.
        """
        self.data = pd.read_json(self.data_fname)

    def show_age_distrib(self) -> Tuple[np.ndarray, np.ndarray]:
        """Calculates and plots the age distribution of the participants.

        Returns
        -------
        hist : np.ndarray
            Number of people in a given bin
        bins : np.ndarray
            Bin edges
        """
        bin_edges = np.linspace(0, 100, 11)
        _, ax = plt.subplots()
        hist_values, bin_edges, _ = ax.hist(self.data["age"], bins=bin_edges)
        ax.set_xlabel("Age")
        ax.set_ylabel("Counts")
        ax.set_title("Age distribution across all subjects")
        return hist_values, bin_edges

 
    def remove_rows_without_mail(self) -> pd.DataFrame:
        """Checks self.data for rows with invalid emails, and removes them.

        Returns
        -------
        pd.DataFrame
            A corrected DataFrame, i.e. the same table but with the erroneous rows removed and
            the (ordinal) index after a reset.
        """
        valid_email = self.data["email"].apply(
            lambda x: self._validate_email(x)
        )
        return self.data.loc[valid_email].reset_index(drop=True)

    def _validate_email(self, email: str) -> bool:
        """Checks if an email is valid.

        Parameters
        ----------
        email : str
            The string to validate

        Returns
        -------
        bool
            True if email is valid, False otherwise
        """
        if "@" not in email or "." not in email:
            return False
        if email.startswith("@") or email.endswith("@"):
            return False
        if email.startswith(".") or email.endswith("."):
            return False
        if not email.isascii():
            return False
        if email.count("@") != 1:
            return False
        if email[email.find("@") + 1] == ".":
            return False
        return True

    def _find_rows_with_nulls(self) -> np.ndarray:
        """Finds rows which contain at least one NA
        and returns their index as an array.

        Returns
        -------
        np.ndarray
            Indices of rows with at least one NA.
        """
        # Select the relevant columns (from "q1" to "q5")
        relevant_columns = self.data.loc[:, "q1":"q5"]
    
        # Identify rows with any null values
        has_nulls = relevant_columns.isna().any(axis=1)
    
        # Get the indices of those rows
        null_rows = has_nulls.index[has_nulls].to_numpy()
    
        return null_rows

    def _fill_na_with_mean(self) -> pd.DataFrame:
        """Fills the dataframe with means instead of NAs.

        To generate the corrected DF we'll construct an identically-sized DF
        that contains only the means per students, and we'll use the "where"
        method to swap the NA values with the values from the "means" DataFrame.

        Returns
        -------
        pd.DataFrame
            DF with the mean of the row instead of the NA value
        """
        grades_df = self.data.loc[:, "q1":"q5"]
        row_means = grades_df.mean(axis=1)
        means_df = pd.DataFrame({col: row_means for col in grades_df.columns})
        filled_df = grades_df.where(grades_df.notnull(), means_df)
        return filled_df
    


    def fill_na_with_mean(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """Finds, in the original DataFrame, the subjects that didn't answer
        all questions, and replaces that missing value with the mean of the
        other grades for that student.

        Returns
        -------
        2-tuple of (pd.DataFrame, np.ndarray)
            The corrected DataFrame after insertion of the mean grade and row
            indices of the students that their new grades were generated
        """
        null_rows = self._find_rows_with_nulls()
        filled_grades_df = self._fill_na_with_mean()
        updated_df = self.data.copy()
        updated_df.loc[:, "q1":"q5"] = filled_grades_df
        return updated_df, null_rows

    def score_subjects(self, maximal_nans_per_sub: int = 1) -> pd.DataFrame:
        """Calculates the average score of a subject and adds a new "score" column
        with it.

        If the subject has more than "maximal_nans_per_sub" NaN in his grades, the
        score should be NA. Otherwise, the score is simply the mean of the other grades.
        The datatype of score should be 'UInt8', and the floating point raw numbers should be
        rounded down before the conversion.

        Parameters
        ----------
        maximal_nans_per_sub : int, optional
            Number of allowed NaNs per subject before giving a NA score.

        Returns
        -------
        pd.DataFrame
            A new DF with a new column - "score".
        """
        question_columns = self.data.loc[:, "q1":"q5"]
        self.data["score"] = (
            question_columns.mean(axis=1).astype("uint8").astype("UInt8")
        )
        more_than_maximal_nans_row_indices = (
            question_columns.isna().sum(axis=1) > maximal_nans_per_sub
        )
        self.data.loc[more_than_maximal_nans_row_indices, "score"] = pd.NA
        return self.data

    def correlate_gender_age(self) -> pd.DataFrame:
        """Looks for a correlation between the gender of the subject, their age
        and the score for all five questions.

        Returns
        -------
        pd.DataFrame
            A DataFrame with a MultiIndex containing the gender and whether the subject is above
            40 years of age, and the average score in each of the five questions.
        """
        df_with_age = self.data.dropna(subset=["age"]).set_index(["gender", "age"], append=True)
        grouped = df_with_age.loc[:, "q1":"q5"].groupby([None, lambda x: x > 40], level=[1, 2])
        return grouped.mean()
    
    
    

q = QuestionnaireAnalysis("/Users/freyaprein/Documents/GitHub/hw5-2024/data.json")
q.read_data()
q.score_subjects()
q.data["score"].to_csv("q4_data.csv")

def compare_files(file1: str, file2: str) -> pd.DataFrame:
    """Compares the 'score' columns of two CSV files.

    Parameters
    ----------
    file1 : str
        Path to the first CSV file.
    file2 : str
        Path to the second CSV file.

    Returns
    -------
    pd.DataFrame
        A DataFrame showing the rows where the scores differ.
    """
    # Load the files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Compare the 'score' columns
    comparison = df1['score'] == df2['score']

    # Identify rows where the scores differ
    differences = df1.loc[~comparison]

    return differences


# Can not find any differences between the produced "score" column and the one provided in the test
differences = compare_files('/Users/freyaprein/Documents/GitHub/hw5-2024/q4_data.csv', '/Users/freyaprein/Documents/GitHub/hw5-2024/tests_data/q4_score.csv')
print(differences)
