import requests
import json
import yaml
import time
import os
from bs4 import BeautifulSoup
import pandas as pd
import argparse
from distutils.util import strtobool
import schedule


def get_atag(data):
    return data.a.text.replace("\n", "").replace(" ", "")


def get_request(task):
    target_url = "https://paperswithcode.com/task/" + task
    r = requests.get(target_url)
    soup = BeautifulSoup(r.text, "lxml")
    return soup


def create_inicsv(task, filepath):
    soup = get_request(task)

    lst_dataset = [
        [get_atag(dataset), get_atag(model), get_atag(paper)]
        for dataset, model, paper in zip(
            soup.select("[class='dataset black-links']"),
            soup.select("[class='black-links']"),
            soup.select("[class='paper blue-links']"),
        )
    ]
    df = pd.DataFrame(lst_dataset, columns=("dataset", "model", "paper"))
    df.to_csv(filepath, index=False)


def make_msg(soup, webhook_url, filepath):
    df = pd.read_csv(filepath, index_col=0)
    for dataset, model, paper, url in zip(
        soup.select("[class='dataset black-links']"),
        soup.select("[class='black-links']"),
        soup.select("[class='paper blue-links']"),
        soup.select("[class='text-center paper']"),
    ):
        dataset = get_atag(dataset)
        model = get_atag(model)
        if not (dataset in df.index):
            df.loc[dataset] = [model, paper]
        if df.loc[dataset].iloc[0] != model:
            paper = get_atag(paper)
            url = url.a.get("href")
            paperurl = "https://paperswithcode.com" + url
            lst_text = [
                "*** State-of-the-Art Updated! ***",
                "DATASET: " + dataset,
                "BEST MODEL: " + df.loc[dataset].iloc[0] + " ==> " + model,
                "PAPER TITLE: " + df.loc[dataset].iloc[1] + " ==> " + paper,
                paperurl,
            ]
            text = "\n".join(lst_text)
            if webhook_url is not None:
                requests.post(
                    webhook_url,
                    data=json.dumps(
                        {"text": text},
                    ),
                )
            time.sleep(1)
            df.loc[dataset].iloc[0] = model
            df.loc[dataset].iloc[1] = paper
    df.to_csv(filepath)


def check_update(webhook_url: str, lst_tasks: list, needsInitialCsv: int) -> None:
    for task in lst_tasks:
        soup = get_request(task)
        filepath = os.path.join(os.getcwd(), task + ".csv")
        if needsInitialCsv or not os.path.isfile(filepath):
            print(f"Creating CSV file of {task}")
            create_inicsv(task, filepath)
        else:
            print(f"Making Slack msg of {task}")
            make_msg(soup, webhook_url, filepath)
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="bot")
    parser.add_argument("--webhook_url", type=str, help="incoming webhook url")
    parser.add_argument(
        "--needsInitialCsv", type=strtobool, default=False, help="initial file"
    )
    args = parser.parse_args()

    with open(os.path.join(os.getcwd(), "config.yaml")) as file:
        obj = yaml.safe_load(file)
    print(obj)

    # every day
    schedule.every().day.at(obj["time"]).do(
        check_update,
        webhook_url=args.webhook_url,
        lst_tasks=obj["tasks"],
        needsInitialCsv=args.needsInitialCsv,
    )

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
