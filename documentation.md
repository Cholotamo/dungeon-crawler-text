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
I noticed that once the loop ends (when we decide it ends), each civilization, dungeon, location, won't really have a fleshed out history. I may need to introduce an Assistant Historian that is called up for each 'object' (city, dungeon, ). 

For each historical turn, we feed that response to the assistant.
In that response, each time an object is mentioned, we create or update an entry of it in a registry.