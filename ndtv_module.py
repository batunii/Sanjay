def get_from_ndtv(soup) -> dict:
    link_headline_dict = {}
    boxes = soup.find_all("div", class_="nshp_widget_boxwrap")
    # dates = soup.find_all("span", class_="nshp_news_sbh_inactive")
    # print(dates)
    for box in boxes:
        # print(f"This is box : {box} \n")
        titles = box.find_all(["h1", "div"], class_="nshp_news_headline")
        for title in titles:
            link_tag = title.find("a")
            link = link_tag["href"]
            headline = link_tag.get_text(strip=True)
            link_headline_dict[headline] = link
    return link_headline_dict

        # print(f"{dates[i]=}")
    # link = title.find("a")
    # if link.has_attr('href'):
    # print(f"{link['href']=}")
    # article = Article(link['href'])
    # article.download()
    # article.parse()
    # print(f"{article.text}")
