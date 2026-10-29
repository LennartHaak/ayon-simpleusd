Used to clean up landing README and to move Todos here
- ## Bugs:
  - ### Root Asset Loader:
    - Transform inside group is set to transform everything with payload not just the referenced file
    - When Loading asset it looses structure type assignments without SimpleUSD_Asset_Structure have to bake it

- ## Automatic Turntables:
  - ### Needs:
    - Model rotation
    - Light Rotation
    - Maybe different perspectives?
      - Close ups
      - Top perspective

  - ### Types:
    - Model Turntable
      - Loads:
        - Model

    - Shading Turntable
      - Loads:
        - Model
        - Shading

    - FX/Groom Turntable
      - Loads:
        - Model
        - FX/Groom
        - maybe shading?

    - Root turntable
      - Loads:
        - All layers
          - Idk how to have this implemented cleanly, I don't want to have a
            new Root turntable every time some updates a layer to not block
            RoyalRender

  - ### Implementation notes:
    - renders should be saved inside the tasks folder. We don't need anything inside
      the work folder turntables can just be saved once and inside the publish folder
      - Project -> Assets --> Asset type --> Asset -> publish -> Task -> Turntable
    - Turntable version should have the version number of the publish
    - Has to be a rendered reviewable to upload to AYON
    - Turntable should render on Farm

- ## Render
  - ### Implementation notes
    - copy remainder frames toggle disappeared
      - add a toggle for from work or publish folder
      - copy remainder frames is on by default but doesn't find the previous frames
        because we moved the save structure around
    - Add a second group input field that can be used to select what PCs the
      packing happens on. Not just what everything renders on
    - Add a toggle that reuses the render package from a previous version
    - rendering locally and packing locally seems to be broken for some reason
    - Render logs show no info about how long the packing takes. Just that its
      happening. Can we add a progress indicator to the render logs? Same with
      FFMPEG
    - FFMPEG has a green box when it has no image to put into the comparison review
      Can we just have a black frame there?
    - Be able to set frame range for render package
    - Is there a way to split packing into a single render package between pcs or
      have multiple packages if thats faster 
    - OpenGL/Flipbooks should also render on farm

  - ### Errors
    - For some reason Breakdown sh010 didn't render without flattening the stage. idk why this error didn't happen before. But maybe we should just flatten the stage when rendering and just take the file size hit
  - We would otherwise prolly need a USD configure to save everything next to the publish. That would be cleaner but file size wouldn't be smaller I guess
  - It was fixed when either flattenstage which isn't an option because filesize and when I said keep references and Sublayers. Idk why this didn't have to be done before and maybe its just Houdini 21

- ## FX Publishing
  - HDA wip
  - Farm caching?

- ## Animation Workflow
  - Not started

- ## Rig Workflow
  - Not started

- ## Misc
  - Camera publish and read
  - Have assets when loaded into a shot be already put into the correct location in the structure
  - have HDA or other way to have lights to get put into correct location in USD Structure
  - Shots need a root file
  - Install Ayon on all pcs and add to ayon group in RR
