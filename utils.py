# utils.py
def strip_html(content):
    """Strips HTML tags from content using BeautifulSoup."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")
    return soup.get_text()
