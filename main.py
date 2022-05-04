import time
import random
from typing import Optional
from abc import (
    ABC,
    abstractmethod,
)

import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import unquote
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

headers = {
    'accept': '*/*',
    'user-agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36'
    )
}
url = (
    'https://spb.zoon.ru/medical/?search_query_form='
    '1&m%5B5200e522a0f302f066000055%5D=1&center%5B%5D='
    '59.91878264665887&center%5B%5D=30.342586983263384&zoom=10'
)
path_to_driver = '/home/gideon/projects/selenium/driver/chromedriver'
path_to_file_dir = 'data'


class ICommand(ABC):
    """
    Интерфейсный класс для выполняемых операций
    """

    @abstractmethod
    def execute(self) -> None:
        pass


class SeleniumParser(ICommand):

    def __init__(
        self, url: str,
        path_to_driver: str,
        path_to_html_file: str,
    ) -> None:
        self.url = url
        self._service = Service(executable_path=path_to_driver)
        self.driver = webdriver.Chrome(service=self._service)
        self.path_to_html_file = path_to_html_file

    def execute(self) -> None:
        self._get_source_html()

    def _get_source_html(self) -> None:
        self.driver.maximize_window()

        try:
            self.driver.get(url=self.url)
            self.driver.implicitly_wait(5)
            while True:
                self.driver.execute_script(
                    'window.scrollTo(0, window.scrollY + 5000)'
                    )

                if self.driver.find_elements(
                    by=By.CLASS_NAME,
                    value='hasmore-text'
                ):
                    with open(
                        'data/source-page.html', 'w',
                        encoding='utf-8'
                    ) as file:
                        file.write(self.driver.page_source)
                    print('[INFO] HTML file copied successfully!')
                    break
                self.driver.implicitly_wait(2)
        except WebDriverException as ex:
            print('[ERROR] ' + str(ex))
        finally:
            self.driver.close()
            self.driver.quit()


class FileParser(ICommand):

    def __init__(
        self,
        path_to_html_file: str,
        path_to_url_json_file: str,
    ) -> None:
        self.path_to_html_file = path_to_html_file
        self.path_to_url_json_file = path_to_url_json_file

    def execute(self) -> None:
        self._get_items_urls()

    def _get_items_urls(self) -> None:
        try:
            with open(self.path_to_html_file, 'r', encoding='utf-8') as file:
                src = file.read()
            soup = BeautifulSoup(src, 'lxml')
            items_divs = soup.find_all('h2', class_='minicard-item__title')
            urls = {index: item.find('a').get('href') for index, item in
                enumerate(
                    items_divs,
                    start=1
                )}

            with open(self.path_to_url_json_file, 'w') as file:
                json.dump(urls, file, indent=4, ensure_ascii=False)

            print('[INFO] Urls collected successfully!')

        except (FileNotFoundError, AttributeError) as ex:
            print('[ERROR] ' + str(ex))


class RequestParser(ICommand):

    def __init__(
        self,
        path_to_url_json_file: str,
        path_to_result_json_file: str,
        headers: dict[str]
    ) -> None:
        self.path_to_url_json_file = path_to_url_json_file
        self.path_to_result_json_file = path_to_result_json_file
        self.headers = headers

    def execute(self) -> None:
        self._get_data()

    def _get_data(self):
        try:
            with open(
                self.path_to_url_json_file,
                'r',
                encoding='utf-8'
            ) as file:
                data: dict = json.load(file)

            result_list = []
            urls_count = len(data.keys())
            count = 1

            for key, value in data.items():

                response = requests.get(
                    url=value,
                    headers=self.headers,
                )
                soup = BeautifulSoup(response.text, 'lxml')
                result_list.append(
                    {
                        'item_name': self._get_item_name(soup=soup),
                        'item_url': value,
                        'item_phones_list': self._get_item_phones_list(
                            soup=soup
                        ),
                        'item_address': self._get_item_address(soup=soup),
                        'item_site': self._get_item_site(soup=soup),
                        'social_networks_list': self._get_social_network_list(
                            soup=soup
                        )
                    }
                )

                time.sleep(random.randrange(2, 5))

                if count % 10 == 0:
                    time.sleep(random.randrange(5, 9))

                print(f'[+] Processed: {count}/{urls_count}')

                count += 1

            with open(
                self.path_to_result_json_file,
                'w',
                encoding='utf-8'
            ) as file:
                json.dump(result_list, file, indent=4, ensure_ascii=False)

            print('[INFO] Data collected successfully!')
        except FileNotFoundError as ex:
            print('[ERROR] ' + str(ex))

    def _get_item_name(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            item_name = soup.find(
                'span', {'itemprop': 'name'}
            ).text.strip()
        except AttributeError:
            item_name = None
        return item_name

    def _get_item_phones_list(
        self,
        soup: BeautifulSoup,
    ) -> Optional[list[str]]:
        try:
            item_phones = soup.find(
                'div', class_='service-phones-list'
            ).find_all(
                'a', class_='js-phone-number'
            )
            item_phones_list = [
                phone.get('href').split(':')[-1].strip()
                for phone in item_phones
            ]
        except AttributeError:
            item_phones_list = None

        return item_phones_list

    def _get_item_address(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            item_address = soup.find(
                'address',
                class_='iblock'
            ).text.strip()
        except AttributeError:
            item_address = None
        return item_address

    def _get_item_site(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            item_site = soup.find(
                'div',
                class_='service-website-value'
            ).find('a').text.strip()
        except AttributeError:
            item_site = None
        return item_site

    def _get_social_network_list(
        self,
        soup: BeautifulSoup,
    ) -> Optional[list[str]]:
        try:
            item_social_networks = soup.find(
                'div', class_='service-description-social-list'
            ).find_all('a')
            social_networks_list = [
                unquote(sn.get('href').split('?to=')[1].split('&')[0])
                for sn in item_social_networks
            ]
        except AttributeError:
            social_networks_list = None

        return social_networks_list


class Command:

    def __init__(self):
        self.history: list[ICommand] = []

    def add_command(self, command: ICommand) -> None:
        self.history.append(command)

    def get_result(self) -> None:
        if not self.history:
            print('Не задана очередность выполнения')
        else:
            for executor in self.history:
                executor.execute()
        self.history.clear()


if __name__ == '__main__':
    path_to_html_file = path_to_file_dir + '/source-page.html'
    path_to_url_json_file = path_to_file_dir + '/urls.json'
    path_to_result_json_file = path_to_file_dir + '/result.json'
    command = Command()
    selenium_parser = SeleniumParser(
        url=url,
        path_to_driver=path_to_driver,
        path_to_html_file=path_to_html_file,
    )
    file_parser = FileParser(
        path_to_html_file=path_to_html_file,
        path_to_url_json_file=path_to_url_json_file,
    )
    request_parser = RequestParser(
        headers=headers,
        path_to_url_json_file=path_to_url_json_file,
        path_to_result_json_file=path_to_result_json_file
    )
    command.add_command(selenium_parser)
    command.add_command(file_parser)
    command.add_command(request_parser)
    command.get_result()
