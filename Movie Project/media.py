import webbrowser

"""this class constructs a Movie object, and contains 6 attributes: title, storyline,
poster image URL, youtube trailer URL, release date and cast list. """
class Movie():
    def __init__(self, movie_title, movie_storyline, poster_image,
                 trailer_youtube, released_date, cast_list):
        """this is the constructor method which takes the 6 attributes as inputs
        and turns them into properties of the object created. """
        self.title = movie_title
        self.storyline = movie_storyline
        self.poster_image_url = poster_image
        self.trailer_youtube_url = trailer_youtube
        self.release_date = released_date
        self.cast = cast_list
