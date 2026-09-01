# 01/09/2026
I have tried running the simulation on a full 5 epochs, there are some issues.

1. The quality is remarkably poorer when using the gemini flash models. Particularly, between epochs, objects will move places, and also object placements and dimensions sometimes don't make sense (The Historian described a plateau, the Cartographer only made a 2x2 box of cliffs, fair enough. But in a later epoch, when a civilization makes their home on top of the plateau, the Cartographer doesn't place it on the plateau, but rather to the side of it.)

I do not want to invest more money into going the OpenAI route, so I should think more about how to optimize the simulation. Some things I could do is:
  - Enable  *code interpreter* for the Cartographer, and instruct it to use that when generating maps.
  - For the Historian, and ask it to observe the map first before making decisions on what happens next in the chronicle. 
  - Let the agents ask each other questions a little if unsure about things.

2. There are alot of instances of 503 errors. I need a *retry mechanism*.

3. The repeating names are so boring, maybe I can give the Historian a knowledge-base for a made up language to refer to when thinking up names. The geography seems repeated too, maybe another source or enabling online search will help with diversity.

# 31/08/2026
We explore the usage of LLM's collaborating with each other to create an actual cohesive environment that can immerse players.

For now, we have the Cartographer and the Historian. 

The Cartographer is in charge of building the physical artifacts of the world's features.

The Historian is given free reign to think of whatever it wants, more like a world builder, really.

The collaboration currently works like this:
1. Cartographer is initiated and it asks "what is the lay of the land"?
2. Historian gives a description of the geography of the world
3. Cartographer draws the world, void of activity, mostly just nature. Now it asks "what happens next to this land?" It will now ask this continuously in a back-and-forth with the Historian.
4. Each time to answer the Cartographer, the Historian describes the movement and actions of civilizations, their rises and falls.

## What's next?

### Solidify map artifacs generation
We need a solid foundation for location coordinates and a cohesive world matrix. 

### Locale background
I noticed that once the loop ends (when we decide it ends), each civilization, dungeon, location, won't really have a fleshed out history. I may need to introduce an Assistant Historian that is called up for each 'object' (city, dungeon, ). 

For each historical turn, we feed that response to the assistant.
In that response, each time an object is mentioned, we create or update an entry of it in a registry.