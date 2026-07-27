import{at as e,l as t,m as n,p as r,st as i,v as a,w as o,y as s}from"./ui-wC2GCM-8.js";import{L as c}from"./index-RPCgG-2I.js";import{d as l,f as u,l as d,n as f,p,u as m}from"./embed-DpaTuuw2.js";import{t as h}from"./use-compact-C_MUT35M.js";var g=`+--------+
|        |
| @3M4+H |
|        |
+--------+
`,_=`+---------+
|         |
|    >  x |
|    ]  ] |
| @2bx  H |
|         |
+---------+
`,v=`+-----+
|     |
|@  H |
|     |
|     |
+-----+`,y=`+----+
|    |
|@4 H|
|    |
+----+
`,b=`+-------+
|       |
|@4  M v|
|       |
|H W  3<|
|       |
+-------+
`,x=`+-----+      
|@3s v|   +-+
|     |>->|O|
|H   <|   +-+
+-----+      
`,S=`   +-+        
   |I|        
   +-+        
    v         
    v         
+-------+  +-+
|@2Wr*sH|>>|O|
+-------+  +-+
`,C=`+---------+  +-+
|@\`123\`s H|>>|O|
+---------+  +-+
`,w=`+----------+      
|>   v     |   +-+
|    \`     |>->|O|
| @ \`123\`sv|   +-+
|^ s\`1 2\` <|      
|          |      
|    1     |      
|    \`     |      
|    s     |      
|    H     |      
+----------+      
`,T=`+---+    +---+
|>@v|    |>@v|
|   |    |   |
|^ <|    |^ <|
+---+    +---+
`,E=`+------+  +-+
|@3b5v |>>|O|
| >  v |  +-+
|Hdms< |
+------+
`,D=`+---+
|>@v|
|   |
|^ <|
+---+
`,O=`+----+    +---+
|    |    |   |
|@2sH|>-->|@rH|
|    |    |   |
+----+    +---+
`,k=`             +-----+
             |@   v|
+--------+   |     |
| @2sss v|>->|v   <|
| H   s <|   |     |
+--------+   |>  rH|
             +-----+
`,A=`          +------+       
          |@4sssH|       
          +------+       
             v           
             |           
             v           
+-----+   +----+         
|@1v  |   |>@Rv|   +----+
|  >s<|>->|    |>->|@>r<|
+-----+   |    |   +----+
          |^ S<|         
          +----+         
             v           
             |           
             v           
          +----+         
          |@>r<|         
          +----+         
`,j=`+-----+
|     |
| @   |
|     |
|     |
+-----+`,M=`       +----------+     +===+
+-+    |@9b>rsmdv |     :   :
|I|>-->|   ^   <  |>--->:   :
+-+    |          |     :   :
       |          |     +===+
       |        1 |       ^  
       |        s |>------^  
       |        H |          
       +----------+          
`,N=`+------+  +------------+        
|v1W1@<|  |            |  +====+
|> s+v |>>| >@8br>smdv |>>:    :
|^   < |  |      ^  <  |  :    :
+------+  |          r |  :    :
          |          s |  :    :
          | ^        < |  +====+
          |            |    ^   
          +------------+    |   
                   ^  v     |   
                   ^  >-----^   
         +-+  +-----+           
         |I|>>|@r>s<|           
         +-+  +-----+           
`,P=`+-----------------+            
|@\`10\`sW1W+s\`15\`sv|            
|v\`42\`s+s\`91\`s+  <|            
|>s+s\`31\`s\`37\`s  v|            
|vs+s+s\`74\`s\`34\` <|            
|>+s+sH           |            
+-----------------+            
           v                   
           |>--------v         
           v^        |         
      +-------+      v         
      |       |     +=========+
      |  @>rsv|     :         :
      |v     <|     :         :
      |>\`12\`sv|>--->:         :
      |      1|     :         :
      |       |     :         :
      |      s|     :         :
      |   ^  <|     :         :
      +-------+     +=========+
             v       ^         
             >-------^         
`,F=`+------+
| >  H |
|      |
|@Y    |
|      |
| >  H |
+------+
`,I=`+-+
|I|
+-+
 v
 v
+-------+
|  H    |
|  s    |
|  9    |  +-+
|@rX0sH |>>|O|
|  1    |  +-+
|  s    |
|  H    |
+-------+
`,L=i(e()),R=o(),z=Object.fromEntries(Object.entries(Object.assign({"../lessons/arithmetic.man":g,"../lessons/backpack-binary.man":_,"../lessons/first-instruction.man":v,"../lessons/hands1.man":y,"../lessons/hands2.man":b,"../lessons/io1.man":x,"../lessons/io2.man":S,"../lessons/literals1.man":C,"../lessons/literals2.man":w,"../lessons/lockstep.man":T,"../lessons/loop.man":E,"../lessons/movement.man":D,"../lessons/pipes1.man":O,"../lessons/pipes2.man":k,"../lessons/pipes3.man":A,"../lessons/room.man":j,"../lessons/screen1.man":M,"../lessons/screen2.man":N,"../lessons/screen3.man":P,"../lessons/split.man":F,"../lessons/turning.man":I})).map(([e,t])=>[e.replace(/^.*\/(.+)\.man$/,`$1`),t]));function B(e){let t=z[e];if(!t)throw Error(`no lesson program "${e}" — add app/lessons/${e}.man (have: ${Object.keys(z).join(`, `)})`);return t}var V=[4,6,8,12,20,28,36,44],H=5;function U(e){return V[Math.max(0,Math.min(V.length-1,H+e))]}function W(e){let t=[];for(let n of e){let e=t[t.length-1];e&&e[0].id===n.id?e.push(n):t.push([n])}return t}function G({id:e,spec:t}){let n=h(),r=(t.zoomLevel??0)-+!!n;return(0,R.jsx)(`div`,{style:{height:t.height??380,border:`2px solid var(--color-blue-800)`,borderRadius:6,overflow:`hidden`,position:`relative`,margin:`16px 0 8px`},children:(0,R.jsx)(f,{source:{mode:`fixed`,id:`lesson-${e}`,text:B(t.program)},io:t.io?{mode:`panel`,persist:!1,...t.io}:{mode:`none`},editable:!0,showHeader:!0,fileActions:!1,showStepCounter:!1,showFootprint:!1,showToolPalette:!1,showReference:!1,showRuntimePanels:t.showRegisters??!1,showPanelControls:!1,initialRoomsCollapsed:t.collapseRooms??null,initialDisplaysCollapsed:t.collapseDisplay??null,initialPipesPinned:t.pinPipes??!1,initialCellSize:r===0?null:U(r),initialTicksPerSecond:t.ticksPerSecond??3})})}var K={tick:`The unit of time. Each tick, every little man executes the instruction he is standing on and then, if possible, takes one step in his current direction.`,blocked:`A little man is blocked when the instruction he is standing on cannot complete yet (for example, receiving from an empty pipe). A blocked man stays where he is and tries again next tick.`,instruction:`A single ASCII character that specifies an operation that a little man should perform.`,error:`A fatal mistake — hitting a wall, stepping on an invalid instruction. An error immediately ends the whole program.`,halt:`A halted little man stops moving and executing instructions. A halted program stops ticking.`,direction:`The way a little man is currently facing — up, down, left, or right. Each tick he tries to step one square that way, unless he is blocked.`,room:`A little man's home. A rectangular area drawn with + at the corners, - along the top and bottom walls, and | along the left and right walls.`,".man":`The canonical file extension for little man programs.`,hand:`Each little man has two hands. Each hand can hold a single integer.`,"main hand":`One of the little man's hands. Labeled 'A' in the littleman editor. Many operations, like running over a number or adding two numbers, change the value in a little man's main hand.`,"off hand":`The other of a little man's hands. Labeled 'B' in the littleman editor. Operations often use the value in a little man's off hand but rarely write to it.`,pipe:`A unidirectional connection between two rooms. Values travel one pipe cell per tick; a pipe can hold as many values as it has cells.`,"io room":`The input room and the output room: special 3x3 rooms containing only the character I or O. Values read from the input room's pipe are the program's input; values sent into the output room's pipe are the program's output.`,backpack:`A container each little man carries, capable of holding one integer. Shown as BP in the littleman editor. A little man cannot look at the value in his backpack, but he can turn based on it.`,operation:`An instruction — see instruction.`,program:`A grid of ASCII characters that one or more little men walk and execute.`,pixel:`A solid block of color that is approximately as large as a little man.`,display:`a rectangular device that can show images on command.`,"display cursor":`The position on a display where the next pixel will be drawn. The cursor advances from left to right and top to bottom as pixels are drawn.`,"display screen buffer":`One of a display's two stored images: current (the image shown on the display) and next (the image being composed). A swap copies next to current.`},q=a.a`
  && {
    font-style: normal;
    color: inherit;
    border-bottom: 1px dotted var(--color-stone-500);
    text-decoration: none;
    cursor: help;
  }
  &&:hover,
  &&:focus {
    color: inherit;
    text-decoration: none;
    border-bottom-color: var(--color-stone-700);
  }
`,J=a(d)`
  max-width: 260px;
  padding: 6px 8px;
  background: var(--color-stone-800);
  color: var(--color-paper);
  font-size: var(--font-size-small);
  font-style: normal;
  line-height: 1.4;
  text-align: left;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  z-index: 20;
`,Y=a.div`
  margin: 0 -6px 8px;
  padding: 2px 6px;
  border-radius: 3px;
  scroll-margin-top: 16px;
  transition: background-color 0.7s ease-out;

  &:target {
    background: var(--color-yellow-200);
    transition: none;
  }
`;function X({name:e,children:t}){return(0,R.jsx)(l,{delayDuration:0,children:(0,R.jsxs)(u,{children:[(0,R.jsx)(p,{asChild:!0,children:(0,R.jsx)(q,{href:`#def-${e}`,children:t??e})}),(0,R.jsx)(m,{children:(0,R.jsx)(J,{side:`top`,align:`start`,sideOffset:6,collisionPadding:8,children:K[e]})})]})})}var Z=[{id:`little men`,title:`Little men and their rooms`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`We represent a little man using an `,(0,R.jsx)(r,{children:`@`}),` symbol.`]}),(0,R.jsxs)(`p`,{children:[`Little men live in `,(0,R.jsx)(X,{name:`room`,children:`rooms`}),` - rectangular areas denoted using the characters `,(0,R.jsx)(r,{children:`+`}),`, `,(0,R.jsx)(r,{children:`-`}),`, and `,(0,R.jsx)(r,{children:`|`}),`. A little man may never be placed outside of a room, and may never leave the room he was placed in.`]}),(0,R.jsxs)(`p`,{children:[`Try running this program - you'll see an`,` `,(0,R.jsx)(X,{name:`error`,children:`error`}),` when the little man tries to leave his room. An error ends the whole program.`]})]}),embed:{program:`room`,height:380}},{id:`instructions`,title:`Instructions`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[(0,R.jsx)(X,{name:`instruction`,children:`Instructions`}),` are ASCII characters that specify behavior that a little man should take. After a little man steps on an instruction, he attempts to execute it. Each step is called a `,(0,R.jsx)(X,{name:`tick`,children:`tick`}),`.`]}),(0,R.jsxs)(`p`,{children:[`The simplest instruction is `,(0,R.jsx)(r,{children:`H`}),`, which tells a little man to`,` `,(0,R.jsx)(X,{name:`halt`,children:`halt`}),` - to stop moving for the duration of a program.`]}),(0,R.jsxs)(`p`,{children:[`Stepping on an invalid instruction is an`,` `,(0,R.jsx)(X,{name:`error`,children:`error`}),`.`]})]}),embed:{program:`first-instruction`,height:380}},{id:`movement`,title:`Movement`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`Unless they are `,(0,R.jsx)(X,{name:`blocked`,children:`blocked`}),` by something, little men attempt to move one square in their current`,` `,(0,R.jsx)(X,{name:`direction`,children:`direction`}),` on every`,` `,(0,R.jsx)(X,{name:`tick`,children:`tick`}),`. Little men always begin moving to the right.`]}),(0,R.jsxs)(`p`,{children:[`Use `,(0,R.jsx)(r,{children:`v`}),` to set a little man's direction to down, `,(0,R.jsx)(r,{children:`<`}),` `,`for left, `,(0,R.jsx)(r,{children:`>`}),` for right, and `,(0,R.jsx)(r,{children:`^`}),` for up.`]})]}),embed:{program:`movement`,height:380}},{id:`hands`,title:`Hands`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`Each little man has two hands which, for clarity, we'll call their`,` `,(0,R.jsx)(X,{name:`main hand`,children:`main hand`}),` (the right hand for 90% of little men) and their `,(0,R.jsx)(X,{name:`off hand`,children:`off hand`}),`. A little man can hold a single integer in each hand. His hands always begin holding the number "0".`]}),(0,R.jsx)(`p`,{children:`When a little man runs over a number, he copies that number into his main hand.`}),(0,R.jsxs)(`p`,{children:[`The editor shows you live information about what is in each little man's hand when a program is running. For brevity, we use `,(0,R.jsx)(r,{children:`A`}),` `,`to refer to the little man's main hand and `,(0,R.jsx)(r,{children:`B`}),` to refer to his off hand.`]}),(0,R.jsxs)(`p`,{children:[`Try running the program below! Notice that `,(0,R.jsx)(r,{children:`A`}),` changes to "4" after the little man runs over the 4.`]})]}),embed:{program:`hands1`,height:380,showRegisters:!0}},{id:`hands`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`To place a value into a little man's off hand you can use `,(0,R.jsx)(r,{children:`M`}),` `,`to `,(0,R.jsx)(`i`,{children:`copy`}),` the value from his main hand, or you can use `,(0,R.jsx)(r,{children:`W`}),` `,`to `,(0,R.jsx)(`i`,{children:`swap`}),` the values in his hands.`]}),(0,R.jsxs)(`p`,{children:[`Here's a program that makes use of both operations. Watch how the`,` `,(0,R.jsx)(r,{children:`A`}),` and `,(0,R.jsx)(r,{children:`B`}),` values change over the course of the program's run.`]})]}),embed:{program:`hands2`,height:380,showRegisters:!0}},{id:`arithmetic`,title:`Arithmetic`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsxs)(`p`,{children:[`Little men are extraordinarily proficient at basic mathematical tasks. The operation `,(0,R.jsx)(r,{children:`+`}),` causes a little man to add the value in his`,` `,(0,R.jsx)(X,{name:`off hand`,children:`off hand`}),` to the value in his`,` `,(0,R.jsx)(X,{name:`main hand`,children:`main hand`}),` and place the result into his main hand - a small example program that adds the numbers "3" and "4" is provided below.`]})}),embed:{program:`arithmetic`,height:380,showRegisters:!0}},{id:`arithmetic`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`Little men can perform other basic arithmetic tasks such as subtraction `,(0,R.jsx)(r,{children:`-`}),`, multiplication `,(0,R.jsx)(r,{children:`*`}),`, division `,(0,R.jsx)(r,{children:`/`}),`, negation `,(0,R.jsx)(r,{children:`N`}),`, and modulo `,(0,R.jsx)(r,{children:`%`}),`. Operations that require two terms use the `,(0,R.jsx)(`i`,{children:`main`}),` hand first ( `,(0,R.jsx)(r,{children:`A - B`}),` not`,` `,(0,R.jsx)(r,{children:`B - A`}),` ) and the little man always places the primary result into his `,(0,R.jsx)(`i`,{children:`main`}),` hand (for division, he places the floored result into his main hand and the remainder into his off hand).`]}),(0,R.jsxs)(`p`,{children:[`Because this is a course on `,(0,R.jsx)(`i`,{children:`computation`}),`, an explanation of binary is out of scope. But mathematically inclined students may appreciate that little men can also perform basic binary operations such as AND `,(0,R.jsx)(r,{children:`&`}),`, OR `,(0,R.jsx)(r,{children:`|`}),`, XOR `,(0,R.jsx)(r,{children:`~`}),`, and left and right shifts `,(0,R.jsx)(r,{children:`{`}),` and `,(0,R.jsx)(r,{children:`}`}),`.`]})]})},{id:`multiple-rooms`,title:`Multiple Rooms`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsxs)(`p`,{children:[`A `,(0,R.jsx)(X,{name:`program`,children:`program`}),` can contain many`,` `,(0,R.jsx)(X,{name:`room`,children:`rooms`}),`, each of which may contain a little man. Rooms may not overlap or nest. All little men in a program move in lockstep.`]})}),embed:{program:`lockstep`,height:380}},{id:`pipes`,title:`Communicating with pipes`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`In the early 1970s, Ken Thompson discovered that little men could use`,` `,(0,R.jsx)(X,{name:`pipe`,children:`pipes`}),` to communicate. A pipe is a unidirectional connection between two rooms.`]}),(0,R.jsxs)(`p`,{children:[`A pipe is drawn using `,(0,R.jsx)(r,{children:`v`}),`, `,(0,R.jsx)(r,{children:`>`}),`, `,(0,R.jsx)(r,{children:`<`}),`, and`,` `,(0,R.jsx)(r,{children:`^`}),` (to establish direction) and `,(0,R.jsx)(r,{children:`-`}),` or `,(0,R.jsx)(r,{children:`|`}),` `,`(depending on if it is traveling horizontally or vertically). Pipes cannot be drawn within rooms.`]}),(0,R.jsxs)(`p`,{children:[`A little man can use `,(0,R.jsx)(r,{children:`s`}),` (send) to copy the value in his`,` `,(0,R.jsx)(X,{name:`main hand`,children:`main hand`}),` into the nearest outgoing pipe connected to his room, and `,(0,R.jsx)(r,{children:`r`}),` (receive) to take a value from the nearest incoming pipe connected to his room and put it into his main hand.`]})]}),embed:{program:`pipes1`,height:400,showRegisters:!0,collapseRooms:!0}},{id:`pipes`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsx)(`p`,{children:`As you may have noticed, it takes a pipe time to move a value - values move one pipe cell per tick. You can always click on a pipe to see what values are currently inside it.`}),(0,R.jsxs)(`p`,{children:[`A pipe that is 5 cells long can hold a maximum of 5 values. Sending data to a pipe that is full will `,(0,R.jsx)(X,{name:`blocked`,children:`block`}),` `,`until there is space, and trying to `,(0,R.jsx)(`i`,{children:`read`}),` from an empty pipe will block until there's a value to read.`]})]}),embed:{program:`pipes2`,height:400,showRegisters:!0,collapseRooms:!0}},{id:`pipes`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsx)(`p`,{children:`A room can have an arbitrary number of pipes connected. Programs with many pipes can be very expressive. In this way, pipes are like garden hoses - you can always screw in another segment when you need to massage data in a new way.`}),(0,R.jsxs)(`p`,{children:[`In addition to `,(0,R.jsx)(r,{children:`r`}),` and `,(0,R.jsx)(r,{children:`s`}),` (which only operate over the`,` `,(0,R.jsx)(`i`,{children:`nearest`}),` incoming or outgoing pipe), little men can read from`,` `,(0,R.jsx)(`i`,{children:`any`}),` incoming pipe with `,(0,R.jsx)(r,{children:`R`}),` and send to `,(0,R.jsx)(`i`,{children:`every`}),` `,`outgoing pipe with `,(0,R.jsx)(r,{children:`S`}),`. Finally, `,(0,R.jsx)(r,{children:`U`}),` is like `,(0,R.jsx)(r,{children:`R`}),`, but, after receiving the value, the little man will turn away from the pipe which he received the value from.`]})]}),embed:{program:`pipes3`,height:460,showRegisters:!0,zoomLevel:-1}},{id:`pipes`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsx)(`p`,{children:`Pipes are the first concept that tends to confuse new students. Remember that you can always click on a pipe to see what values are flowing through it.`}),(0,R.jsxs)(`p`,{children:[`The precise semantics of pipe-drawing, the definition of "nearest," and how ties are broken are described in depth in our`,` `,(0,R.jsx)(s,{to:`/language-reference`,children:`language reference`}),`.`]}),(0,R.jsxs)(`p`,{children:[`But don't fear! The editor is here to help you. You can click on any pipe operation (like `,(0,R.jsx)(r,{children:`r`}),` or `,(0,R.jsx)(r,{children:`s`}),`) to highlight the pipe that it will operate over. And the editor comes with dedicated pipe-drawing tools: view the editor help page to learn more.`]})]})},{id:`input-output`,title:`Input and output`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsx)(`p`,{children:`Fortunately, it is possible to communicate with the little men in our computers. Computers would not be nearly as useful if we couldn't.`}),(0,R.jsxs)(`p`,{children:[`To communicate with our little men we use the`,` `,(0,R.jsx)(X,{name:`io room`,children:`input room`}),` and output room - special 3x3 rooms that contain only the character "I" or "O".`]}),(0,R.jsx)(`p`,{children:`To output a value, simply send it to a pipe that is connected to the output room. Run the program below and notice how the number "3" appears in the output box.`})]}),embed:{program:`io1`,height:400,io:{},showRegisters:!1}},{id:`input-output`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsx)(`p`,{children:`Similarly, read from a pipe connected to the input room in order to receive input. This program receives the number "42" (the input box in the bottom left of the editor), multiplies it by 2, and outputs it.`})}),embed:{program:`io2`,height:400,io:{initialInput:`42`},showRegisters:!1}},{id:`input-output`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsxs)(`p`,{children:[(0,R.jsx)(X,{name:`program`,children:`Programs`}),` can have at most one input and one output room. It is an error to connect more than one pipe to the input room or the output room, or to connect an input pipe to the output room or vice-versa.`]})})},{id:`turning`,title:`Turning`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`The `,(0,R.jsx)(r,{children:`X`}),` instruction allows a little man to conditionally turn based on the value in his `,(0,R.jsx)(X,{name:`main hand`,children:`main hand`}),`. Upon running an `,(0,R.jsx)(r,{children:`X`}),` `,(0,R.jsx)(X,{name:`operation`,children:`operation`}),`, the little man turns left (counterclockwise) if his main hand is less than 0 and turns right (clockwise) if his main hand is greater than 0. He continues straight if his main hand contains a 0.`]}),(0,R.jsxs)(`p`,{children:[`Try making the input value (in the bottom left) to this program negative, positive, or 0 and observe how the man's direction changes when he hits the `,(0,R.jsx)(r,{children:`X`}),`.`]})]}),embed:{program:`turning`,height:460,io:{initialInput:`4`},showRegisters:!0,zoomLevel:-1}},{id:`backpack`,title:`The backpack`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`In addition to his `,(0,R.jsx)(X,{name:`main hand`,children:`main hand`}),` and`,` `,(0,R.jsx)(X,{name:`off hand`,children:`off hand`}),`, each little man has a`,` `,(0,R.jsx)(X,{name:`backpack`,children:`backpack`}),` (shown as `,(0,R.jsx)(r,{children:`BP`}),` in the editor). The backpack is capable of holding a number. The little man cannot look at the value in his backpack, but he can turn based on it.`]}),(0,R.jsxs)(`p`,{children:[`The `,(0,R.jsx)(r,{children:`b`}),` `,(0,R.jsx)(X,{name:`operation`,children:`operation`}),` copies the value from a little man's main hand into his backpack. `,(0,R.jsx)(r,{children:`m`}),` `,`decrements the value in his backpack by 1.`]}),(0,R.jsxs)(`p`,{children:[`The `,(0,R.jsx)(r,{children:`a`}),` operation causes a little man to turn to the left if his backpack value is greater than 0 - otherwise he goes straight. Likewise, the `,(0,R.jsx)(r,{children:`d`}),` operation turns a little man to the right if his backpack value is greater than 0.`]}),(0,R.jsxs)(`p`,{children:[`Clever use of the backpack allows a little man to do a strange thing we call `,(0,R.jsx)(`i`,{children:`loop`}),` - that is, to repeat an operation multiple times. Here, we place the number "3" into the little man's backpack so that he outputs the number "5" three times!`]})]}),embed:{program:`loop`,height:420,io:{},showRegisters:!0}},{id:`backpack`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`The little man can also make use of his mathematical prowess when reading from the backpack. The `,(0,R.jsx)(r,{children:`x`}),` operation turns the little man to the left (counterclockwise) if the value in his backpack is even, and right otherwise. The `,(0,R.jsx)(r,{children:`]`}),` operation divides the value in his backpack by 2, rounding down.`]}),(0,R.jsxs)(`p`,{children:[`Students of mathematics may recognize `,(0,R.jsx)(r,{children:`x`}),` as a turn based on the value of `,(0,R.jsx)(r,{children:`backpack & 1`}),` and `,(0,R.jsx)(r,{children:`]`}),` as`,` `,(0,R.jsx)(r,{children:`backpack = backpack >> 1`}),`.`]})]}),embed:{program:`backpack-binary`,showRegisters:!0}},{id:`backpack`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsxs)(`p`,{children:[`The backpack has additional functionality not directly related to turning: the `,(0,R.jsx)(r,{children:`q`}),` operation reads the number of values currently sitting in the nearest incoming pipe into the little man's backpack.`]})})},{id:`bigger numbers`,title:`Bigger numbers`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsxs)(`p`,{children:[`You may sometimes need to write numbers larger than 9 in your`,` `,(0,R.jsx)(X,{name:`program`,children:`program`}),`. To do this, surround the number that you would like to write with `,(0,R.jsx)(r,{children:"`"}),`. A little man loads the entire number between two `,(0,R.jsx)(r,{children:"`"}),` into his`,` `,(0,R.jsx)(X,{name:`main hand`,children:`main hand`}),` upon reaching the closing`,` `,(0,R.jsx)(r,{children:"`"}),`. This program loads and outputs the number "123".`]})}),embed:{program:`literals1`,height:400,io:{},showRegisters:!0}},{id:`bigger numbers`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`Numbers can be written in this fashion vertically and horizontally, and can be walked in any direction. The sequence `,(0,R.jsx)(r,{children:"`123`"}),` could be read as "123" or "321" depending on the direction that it is walked.`]}),(0,R.jsx)(`p`,{children:`You may also leave spaces inside your large numbers - the little man ignores them when deciding what number to store in his main hand.`}),(0,R.jsx)(`p`,{children:`Here is a program with several large numbers - try to predict what numbers it will output!`})]}),embed:{program:`literals2`,height:400,io:{},showRegisters:!0,zoomLevel:-1}},{id:`bigger numbers`,body:(0,R.jsx)(R.Fragment,{children:(0,R.jsxs)(`p`,{children:[`It is an error to place anything other than a space or a number between two `,(0,R.jsx)(r,{children:"`"}),` `,(0,R.jsx)(X,{name:`operation`,children:`operations`}),`, and it is an error to place an unmatched `,(0,R.jsx)(r,{children:"`"}),` in your program.`]})})},{id:`the-display`,title:`The LM-75 display`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`You are likely reading this textbook on a`,` `,(0,R.jsx)(X,{name:`display`,children:`display`}),` - a rectangular device that can show images on command. While the implementation of displays is outside the scope of this course, controlling one is relatively simple.`]}),(0,R.jsxs)(`p`,{children:[`In this class you will use an LM-75 display with a maximum interior width and height of 64 `,(0,R.jsx)(X,{name:`pixel`,children:`pixels`}),`. LM-75s are drawn using `,(0,R.jsx)(r,{children:`+`}),`, `,(0,R.jsx)(r,{children:`:`}),`, and `,(0,R.jsx)(r,{children:`=`}),`. Changing the image on an LM-75 involves writing data over `,(0,R.jsx)(X,{name:`pipe`,children:`pipes`}),`. However, unlike rooms, the `,(0,R.jsx)(`i`,{children:`side`}),` that a pipe attaches to is significant (readers have likely encountered VGA connectors like this at home).`]}),(0,R.jsx)(`p`,{children:`Before we discuss the LM-75's precise specification, let us consider a simple example program that uses a display. Try running this program and observe how the display changes!`})]}),embed:{program:`screen1`,height:380,showRegisters:!0,zoomLevel:-1,ticksPerSecond:100,io:{initialInput:`0 1 2 3 4 5 6 7 8`},collapseRooms:!0,collapseDisplay:!0}},{id:`the-display`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`How does such a simple program produce such a complex image? To answer that, we must understand the core concepts of a display: the`,` `,(0,R.jsx)(X,{name:`display cursor`,children:`cursor`}),` and the`,` `,(0,R.jsx)(X,{name:`display screen buffer`,children:`screen buffers`}),`.`]}),(0,R.jsxs)(`p`,{children:[`Pixels are drawn one at a time. The LM-75's `,(0,R.jsx)(`i`,{children:`cursor`}),` points to the next pixel that the display will draw. It begins pointing at the upper-left pixel of the display, and it automatically advances from left to right and top to bottom whenever a pixel is drawn.`]}),(0,R.jsxs)(`p`,{children:[`The LM-75 has two `,(0,R.jsx)(`i`,{children:`screen buffers`}),`, which we call `,(0,R.jsx)(`i`,{children:`current`}),` `,`and `,(0,R.jsx)(`i`,{children:`next`}),`. Current contains the image currently shown on the display; next is where the next image to show is composed. Showing a new image is simply a matter of copying next to current.`]}),(0,R.jsxs)(`p`,{children:[`To draw to the LM-75, attach a pipe to its `,(0,R.jsx)(`i`,{children:`left`}),` side. When the LM-75 reads a value from its left side it:`]}),(0,R.jsxs)(`ul`,{children:[(0,R.jsx)(`li`,{children:`Looks up the color for that value`}),(0,R.jsx)(`li`,{children:`Draws that pixel to next at the cursor's current position`}),(0,R.jsx)(`li`,{children:`Advances the cursor`})]}),(0,R.jsx)(`p`,{children:`The LM-75 supports 16 colors, so values that arrive over the left pipe must be between 0 and 15.`}),(0,R.jsxs)(`p`,{children:[`To tell the LM-75 to display the next buffer, attach a pipe to its`,` `,(0,R.jsx)(`i`,{children:`bottom`}),` side. Writing a `,(0,R.jsx)(r,{children:`0`}),` copies next to current, clears next, and repositions the cursor in the upper left. Writing a`,` `,(0,R.jsx)(r,{children:`1`}),` copies next to current but preserves the cursor's position and the state of next.`]}),(0,R.jsx)(`p`,{children:`Inspect the program below. Try changing its input from 0 to 1 and see how the program's behavior changes. Also note that you can inspect the screen's state as your program runs by clicking on the widget that appears below it.`})]}),embed:{program:`screen2`,height:420,showRegisters:!0,zoomLevel:-1,ticksPerSecond:30,collapseRooms:!0,io:{initialInput:`0`}}},{id:`the-display`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsxs)(`p`,{children:[`Pipes may also be attached to the `,(0,R.jsx)(`i`,{children:`top`}),` of the LM-75. A value written to this pipe repositions the cursor. These values take the form `,(0,R.jsx)(r,{children:`row * width + column`}),` (rows and columns are counted from 0). For example, on a 4x4 display, write `,(0,R.jsx)(r,{children:`6`}),` to position the cursor in the third column of the second row, and `,(0,R.jsx)(r,{children:`15`}),` to position the cursor in the bottom right.`]}),(0,R.jsx)(`p`,{children:`Changing the cursor's position allows your programs to quickly draw interesting shapes and images! Run the program below for a simple example.`})]}),embed:{program:`screen3`,height:380,showRegisters:!0,zoomLevel:-2,ticksPerSecond:30,collapseRooms:!0}},{id:`further study`,title:`Further study`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsx)(`p`,{children:`This wraps up our whirlwind tour of your computer's architecture. You are now ready to begin your homework.`}),(0,R.jsxs)(`p`,{children:[`To get started, take a look at`,` `,(0,R.jsx)(s,{to:`/grading`,hash:`grading`,children:`how problems are graded`}),`, and then visit the `,(0,R.jsx)(s,{to:`/problem-sets`,children:`problem sets`}),` page to try your first problem.`]}),(0,R.jsxs)(`p`,{children:[`To clear up any ambiguities and view the full list of supported`,` `,(0,R.jsx)(X,{name:`operation`,children:`operations`}),`, check out the`,` `,(0,R.jsx)(s,{to:`/language-reference`,children:`language reference and instruction set`}),`. For help with the editor, view the`,` `,(0,R.jsx)(s,{to:`/editor-help`,children:`editor help page`}),`.`]}),(0,R.jsxs)(`p`,{children:[`Whether you're a new student eager to write your first`,` `,(0,R.jsx)(X,{name:`program`,children:`program`}),` or an experienced practitioner who's ready to develop their own methods of creating littleman programs, we're excited to see what you do!`]})]})},{id:`split`,title:`Split`,body:(0,R.jsxs)(R.Fragment,{children:[(0,R.jsx)(`p`,{children:(0,R.jsx)(`i`,{children:`The little man grabs his fork, eats a big meal, and splits in two.`})}),(0,R.jsxs)(`p`,{children:[`It is occasionally useful to have two little men team up on a task within the same room. To do this you can use `,(0,R.jsx)(r,{children:`Y`}),`, an instruction that causes the little man to split in two. The newly spawned little men travel perpendicular to the original little man's path. Both little men carry the contents in the original man's hands and backpack.`]}),(0,R.jsxs)(`p`,{children:[`See the `,(0,R.jsx)(s,{to:`/split`,children:`split page`}),` for more details.`]})]}),embed:{program:`split`,height:340}}];function Q(){let{isPending:e}=c(),i=!e;return(0,L.useEffect)(()=>{if(!i)return;let e=decodeURIComponent(window.location.hash.slice(1));if(!e)return;let t=requestAnimationFrame(()=>{document.getElementById(e)?.scrollIntoView()});return()=>cancelAnimationFrame(t)},[i]),e?(0,R.jsx)(n,{children:(0,R.jsx)(`p`,{children:`Loading…`})}):(0,R.jsxs)(n,{style:{maxWidth:760},children:[(0,R.jsx)(`h1`,{children:`Introduction to Systems Programming`}),(0,R.jsxs)(`p`,{children:[`This class will serve as an introduction to `,(0,R.jsx)(`i`,{children:`systems programming`}),` - the act of directly interfacing with the underlying primitives that power the computer that you're using right now.`]}),(0,R.jsx)(`h2`,{children:`How does a computer work?`}),(0,R.jsx)(`p`,{children:`As some of you likely know, inside your computer are millions (or even billions) of little men.`}),(0,R.jsxs)(`p`,{children:[`Those men are constantly dashing around to find and execute simple`,` `,(0,R.jsx)(X,{name:`instruction`,children:`instructions`}),`. An instruction might, for example, tell a little man to add or subtract two numbers or send a message to another little man.`]}),(0,R.jsxs)(`p`,{children:[`We call the set of instructions that a group of little men executes a`,` `,(0,R.jsx)(X,{name:`program`,children:`program`}),`. The individual instructions of a program are simple, but a program's behavior can be surprisingly complex. Programs can solve difficult mathematical problems, simulate games, and communicate over long distances.`]}),(0,R.jsx)(`p`,{children:`With enough time one could even write a program that simulates the behavior of a little man!`}),(0,R.jsx)(`h2`,{children:`About the language and editor`}),(0,R.jsxs)(`p`,{children:[`Littleman (`,(0,R.jsx)(X,{name:`.man`,children:`.man`}),`) programs are stored as text files full of ASCII characters.`]}),(0,R.jsxs)(`p`,{children:[`For the duration of this course you are free to write your programs in the text editor of your choice or to otherwise generate them in whatever way you see fit. However, many text editors struggle to write`,` `,(0,R.jsx)(r,{children:`.man`}),` programs because of their spatial nature and very long lines of text.`]}),(0,R.jsxs)(`p`,{children:[`To that end, your TAs have written a custom littleman program editor! You'll see the editor embedded below. The editor adds modern affordances like syntax highlighting, copy-paste, and the ability to run`,` `,(0,R.jsx)(r,{children:`.man`}),` programs directly in your web browser.`]}),(0,R.jsxs)(`nav`,{"aria-label":`Course contents`,style:{margin:`20px 0 28px`},children:[(0,R.jsx)(`strong`,{children:`Contents`}),(0,R.jsxs)(`ol`,{style:{margin:`8px 0 0`,paddingLeft:24},children:[W(Z).map(([e])=>(0,R.jsx)(`li`,{style:{marginBottom:4},children:(0,R.jsx)(`a`,{href:`#${e.id}`,children:e.title??e.id})},e.id)),(0,R.jsx)(`li`,{children:(0,R.jsx)(`a`,{href:`#definitions`,children:`Definitions`})})]})]}),W(Z).map(e=>{let[n]=e;return(0,R.jsxs)(`section`,{id:n.id,style:{scrollMarginTop:16},children:[(0,R.jsx)(`h2`,{children:n.title??n.id}),e.map((e,t)=>(0,R.jsxs)(L.Fragment,{children:[e.body,e.embed&&(0,R.jsx)(G,{id:t===0?e.id:`${e.id}-${t+1}`,spec:e.embed})]},t)),(0,R.jsx)(`p`,{style:{marginBottom:32},children:(0,R.jsx)(`a`,{href:`#top`,onClick:e=>{e.preventDefault(),window.scrollTo({top:0})},children:(0,R.jsx)(t,{children:`↑ contents`})})})]},n.id)}),(0,R.jsxs)(`section`,{id:`definitions`,style:{scrollMarginTop:16},children:[(0,R.jsx)(`h2`,{children:`Definitions`}),(0,R.jsx)(`dl`,{style:{margin:0},children:Object.entries(K).map(([e,t])=>(0,R.jsxs)(Y,{id:`def-${e}`,children:[(0,R.jsx)(`dt`,{style:{display:`inline`,fontWeight:700},children:e}),(0,R.jsxs)(`dd`,{style:{display:`inline`,margin:0},children:[` — `,t]})]},e))})]})]})}export{Q as component};