import media

import fresh_tomatoes


#movies list

toy_story2 = media.Movie("Toy Story 2", "A story about toys, duh.",
                        "http://ecx.images-amazon.com/images/I/518G5RSWQBL.jpg", "https://www.youtube.com/watch?v=Lu0sotERXhI",
                        "1999", "<p>Tom Hanks</p><p>Tim Allen</p>")

terminator = media.Movie("Terminator", "A story about terminators, duh.",

                        "http://wrongsideoftheart.com/wp-content/gallery/posters-t/terminator_poster_07.jpg",
                         "https://www.youtube.com/watch?v=c4Jo8QoOTQ4", "1984", "<p>Arnold Schwarzenegger</p><p>Linda Hamilton</p>")

star_wars_v = media.Movie("The Empire Strikes Back", "A story about stars, duh.",
                        "http://t1.gstatic.com/images?q=tbn:ANd9GcTtXwQAEDxEY3E9Nn78H96VZCjlV6hZWPlDd5IpVNyeuzO2vT17", "http://www.youtube.com/watch?v=JNwNXF9Y6kY",
                        "1980", "<p>Mark Hamill</p><p>Harrison Ford</p>")

lotr_3 = media.Movie("The Return of the King", "A story about rings, duh.",
                        "http://www.gstatic.com/tv/thumb/movieposters/33156/p33156_p_v7_ak.jpg", "https://youtu.be/Wmm5SNcjLvo",
                        "2003", "<p>Elijah Wood</p><p>Viggo Mortensen</p>")

#/movies list


movies = [toy_story2, terminator, star_wars_v, lotr_3]


fresh_tomatoes.open_movies_page(movies)
