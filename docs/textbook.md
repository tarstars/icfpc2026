# ICFPC 2026 — Textbook ("Introduction to Systems Programming")

Source: https://icfpcontest2026.com/textbook, captured 2026-07-24 (contest day 1).
The site is a JS single-page app; this document is a faithful reconstruction of
the textbook page from the app bundle (`assets/textbook-9zWRf841.js`). Prose is
verbatim; embedded interactive editors are reproduced as their `.man` program
sources. Related pages (not yet captured): `/language-reference`, `/grading`,
`/problem-sets`, `/editor-help`.

---

This class will serve as an introduction to *systems programming* — the act of
directly interfacing with the underlying primitives that power the computer
that you're using right now.

## How does a computer work?

As some of you likely know, inside your computer are millions (or even
billions) of little men.

Those men are constantly dashing around to find and execute simple
instructions. An instruction might, for example, tell a little man to add or
subtract two numbers or send a message to another little man.

We call the set of instructions that a group of little men executes a program.
The individual instructions of a program are simple, but a program's behavior
can be surprisingly complex. Programs can solve difficult mathematical
problems, simulate games, and communicate over long distances.

With enough time one could even write a program that simulates the behavior of
a little man!

## About the language and editor

Littleman (`.man`) programs are stored as text files full of ASCII characters.

For the duration of this course you are free to write your programs in the
text editor of your choice or to otherwise generate them in whatever way you
see fit. However, many text editors struggle to write `.man` programs because
of their spatial nature and very long lines of text.

To that end, your TAs have written a custom littleman program editor! The
editor adds modern affordances like syntax highlighting, copy-paste, and the
ability to run `.man` programs directly in your web browser.

## Little men and their rooms

We represent a little man using an `@` symbol.

Little men live in rooms — rectangular areas denoted using the characters `+`,
`-`, and `|`. A little man may never be placed outside of a room, and may
never leave the room he was placed in.

Try running this program — you'll see an error when the little man tries to
leave his room. An error ends the whole program.

```
+-----+
|     |
| @   |
|     |
|     |
+-----+
```

## Instructions

Instructions are ASCII characters that specify behavior that a little man
should take. After a little man steps on an instruction, he attempts to
execute it. Each step is called a tick.

The simplest instruction is `H`, which tells a little man to halt — to stop
moving for the duration of a program.

Stepping on an invalid instruction is an error.

```
+-----+
|     |
|@  H |
|     |
|     |
+-----+
```

## Movement

Unless they are blocked by something, little men attempt to move one square in
their current direction on every tick. Little men always begin moving to the
right.

Use `v` to set a little man's direction to down, `<` for left, `>` for right,
and `^` for up.

```
+---+
|>@v|
|   |
|^ <|
+---+
```

## Hands

Each little man has two hands which, for clarity, we'll call their main hand
(the right hand for 90% of little men) and their off hand. A little man can
hold a single integer in each hand. His hands always begin holding the number
"0".

When a little man runs over a number, he copies that number into his main
hand.

The editor shows you live information about what is in each little man's hand
when a program is running. For brevity, we use `A` to refer to the little
man's main hand and `B` to refer to his off hand.

Try running the program below! Notice that `A` changes to "4" after the little
man runs over the 4.

```
+----+
|    |
|@4 H|
|    |
+----+
```

To place a value into a little man's off hand you can use `M` to *copy* the
value from his main hand, or you can use `W` to *swap* the values in his
hands.

Here's a program that makes use of both operations. Watch how the `A` and `B`
values change over the course of the program's run.

```
+-------+
|       |
|@4  M v|
|       |
|H W  3<|
|       |
+-------+
```

## Arithmetic

Little men are extraordinarily proficient at basic mathematical tasks. The
operation `+` causes a little man to add the value in his off hand to the
value in his main hand and place the result into his main hand — a small
example program that adds the numbers "3" and "4" is provided below.

```
+--------+
|        |
| @3M4+H |
|        |
+--------+
```

Little men can perform other basic arithmetic tasks such as subtraction `-`,
multiplication `*`, division `/`, negation `N`, and modulo `%`. Operations
that require two terms use the *main* hand first (`A - B`, not `B - A`) and
the little man always places the primary result into his *main* hand (for
division, he places the floored result into his main hand and the remainder
into his off hand).

Because this is a course on *computation*, an explanation of binary is out of
scope. But mathematically inclined students may appreciate that little men can
also perform basic binary operations such as AND `&`, OR `|`, XOR `~`, and
left and right shifts `{` and `}`.

## Multiple Rooms

A program can contain many rooms, each of which may contain a little man.
Rooms may not overlap or nest. All little men in a program move in lockstep.

```
+---+    +---+
|>@v|    |>@v|
|   |    |   |
|^ <|    |^ <|
+---+    +---+
```

## Communicating with pipes

In the early 1970s, Ken Thompson discovered that little men could use pipes to
communicate. A pipe is a unidirectional connection between two rooms.

A pipe is drawn using `v`, `>`, `<`, and `^` (to establish direction) and `-`
or `|` (depending on if it is traveling horizontally or vertically). Pipes
cannot be drawn within rooms.

A little man can use `s` (send) to copy the value in his main hand into the
nearest outgoing pipe connected to his room, and `r` (receive) to take a value
from the nearest incoming pipe connected to his room and put it into his main
hand.

```
+----+    +---+
|    |    |   |
|@2sH|>-->|@rH|
|    |    |   |
+----+    +---+
```

As you may have noticed, it takes a pipe time to move a value — values move
one pipe cell per tick. You can always click on a pipe to see what values are
currently inside it.

A pipe that is 5 cells long can hold a maximum of 5 values. Sending data to a
pipe that is full will block until there is space, and trying to *read* from
an empty pipe will block until there's a value to read.

```
             +-----+
             |@   v|
+--------+   |     |
| @2sss v|>->|v   <|
| H   s <|   |     |
+--------+   |>  rH|
             +-----+
```

A room can have an arbitrary number of pipes connected. Programs with many
pipes can be very expressive. In this way, pipes are like garden hoses — you
can always screw in another segment when you need to massage data in a new
way.

In addition to `r` and `s` (which only operate over the *nearest* incoming or
outgoing pipe), little men can read from *any* incoming pipe with `R` and send
to *every* outgoing pipe with `S`. Finally, `U` is like `R`, but, after
receiving the value, the little man will turn away from the pipe which he
received the value from.

```
          +------+       
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
```

Pipes are the first concept that tends to confuse new students. Remember that
you can always click on a pipe to see what values are flowing through it.

The precise semantics of pipe-drawing, the definition of "nearest," and how
ties are broken are described in depth in our language reference
(`/language-reference`).

But don't fear! The editor is here to help you. You can click on any pipe
operation (like `r` or `s`) to highlight the pipe that it will operate over.
And the editor comes with dedicated pipe-drawing tools: view the editor help
page to learn more.

## Input and output

Fortunately, it is possible to communicate with the little men in our
computers. Computers would not be nearly as useful if we couldn't.

To communicate with our little men we use the input room and output room —
special 3x3 rooms that contain only the character "I" or "O".

To output a value, simply send it to a pipe that is connected to the output
room. Run the program below and notice how the number "3" appears in the
output box.

```
+-----+      
|@3s v|   +-+
|     |>->|O|
|H   <|   +-+
+-----+      
```

Similarly, read from a pipe connected to the input room in order to receive
input. This program receives the number "42" (the input box in the bottom left
of the editor), multiplies it by 2, and outputs it.

```
   +-+        
   |I|        
   +-+        
    v         
    v         
+-------+  +-+
|@2Wr*sH|>>|O|
+-------+  +-+
```

Programs can have at most one input and one output room. It is an error to
connect more than one pipe to the input room or the output room, or to
connect an input pipe to the output room or vice-versa.

## Turning

The `X` instruction allows a little man to conditionally turn based on the
value in his main hand. Upon running an `X` operation, the little man turns
left (counterclockwise) if his main hand is less than 0 and turns right
(clockwise) if his main hand is greater than 0. He continues straight if his
main hand contains a 0.

Try making the input value (in the bottom left) to this program negative,
positive, or 0 and observe how the man's direction changes when he hits the
`X`. (Example input: 4.)

```
+-+
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
```

## The backpack

In addition to his main hand and off hand, each little man has a backpack
(shown as `BP` in the editor). The backpack is capable of holding a number.
The little man cannot look at the value in his backpack, but he can turn based
on it.

The `b` operation copies the value from a little man's main hand into his
backpack. `m` decrements the value in his backpack by 1.

The `a` operation causes a little man to turn to the left if his backpack
value is greater than 0 — otherwise he goes straight. Likewise, the `d`
operation turns a little man to the right if his backpack value is greater
than 0.

Clever use of the backpack allows a little man to do a strange thing we call
*loop* — that is, to repeat an operation multiple times. Here, we place the
number "3" into the little man's backpack so that he outputs the number "5"
three times!

```
+------+  +-+
|@3b5v |>>|O|
| >  v |  +-+
|Hdms< |
+------+
```

The little man can also make use of his mathematical prowess when reading from
the backpack. The `x` operation turns the little man to the left
(counterclockwise) if the value in his backpack is even, and right otherwise.
The `]` operation divides the value in his backpack by 2, rounding down.

Students of mathematics may recognize `x` as a turn based on the value of
`backpack & 1` and `]` as `backpack = backpack >> 1`.

```
+---------+
|         |
|    >  x |
|    ]  ] |
| @2bx  H |
|         |
+---------+
```

The backpack has additional functionality not directly related to turning: the
`q` operation reads the number of values currently sitting in the nearest
incoming pipe into the little man's backpack.

## Bigger numbers

You may sometimes need to write numbers larger than 9 in your program. To do
this, surround the number that you would like to write with `` ` ``. A little
man loads the entire number between two `` ` `` into his main hand upon
reaching the closing `` ` ``. This program loads and outputs the number "123".

```
+---------+  +-+
|@`123`s H|>>|O|
+---------+  +-+
```

Numbers can be written in this fashion vertically and horizontally, and can be
walked in any direction. The sequence `` `123` `` could be read as "123" or
"321" depending on the direction that it is walked.

You may also leave spaces inside your large numbers — the little man ignores
them when deciding what number to store in his main hand.

Here is a program with several large numbers — try to predict what numbers it
will output!

```
+----------+      
|>   v     |   +-+
|    `     |>->|O|
| @ `123`sv|   +-+
|^ s`1 2` <|      
|          |      
|    1     |      
|    `     |      
|    s     |      
|    H     |      
+----------+      
```

It is an error to place anything other than a space or a number between two
`` ` `` operations, and it is an error to place an unmatched `` ` `` in your
program.

## The LM-75 display

You are likely reading this textbook on a display — a rectangular device that
can show images on command. While the implementation of displays is outside
the scope of this course, controlling one is relatively simple.

In this class you will use an LM-75 display with a maximum interior width and
height of 64 pixels. LM-75s are drawn using `+`, `:`, and `=`. Changing the
image on an LM-75 involves writing data over pipes. However, unlike rooms, the
*side* that a pipe attaches to is significant (readers have likely encountered
VGA connectors like this at home).

Before we discuss the LM-75's precise specification, let us consider a simple
example program that uses a display. Try running this program and observe how
the display changes! (Example input: `0 1 2 3 4 5 6 7 8`.)

```
       +----------+     +===+
+-+    |@9b>rsmdv |     :   :
|I|>-->|   ^   <  |>--->:   :
+-+    |          |     :   :
       |          |     +===+
       |        1 |       ^  
       |        s |>------^  
       |        H |          
       +----------+          
```

How does such a simple program produce such a complex image? To answer that,
we must understand the core concepts of a display: the cursor and the screen
buffers.

Pixels are drawn one at a time. The LM-75's *cursor* points to the next pixel
that the display will draw. It begins pointing at the upper-left pixel of the
display, and it automatically advances from left to right and top to bottom
whenever a pixel is drawn.

The LM-75 has two *screen buffers*, which we call *current* and *next*.
Current contains the image currently shown on the display; next is where the
next image to show is composed. Showing a new image is simply a matter of
copying next to current.

To draw to the LM-75, attach a pipe to its *left* side. When the LM-75 reads a
value from its left side it:

- Looks up the color for that value
- Draws that pixel to next at the cursor's current position
- Advances the cursor

The LM-75 supports 16 colors, so values that arrive over the left pipe must be
between 0 and 15.

To tell the LM-75 to display the next buffer, attach a pipe to its *bottom*
side. Writing a `0` copies next to current, clears next, and repositions the
cursor in the upper left. Writing a `1` copies next to current but preserves
the cursor's position and the state of next.

Inspect the program below. Try changing its input from 0 to 1 and see how the
program's behavior changes. Also note that you can inspect the screen's state
as your program runs by clicking on the widget that appears below it.
(Example input: 0.)

```
+------+  +------------+        
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
```

Pipes may also be attached to the *top* of the LM-75. A value written to this
pipe repositions the cursor. These values take the form `row * width + column`
(rows and columns are counted from 0). For example, on a 4x4 display, write
`6` to position the cursor in the third column of the second row, and `15` to
position the cursor in the bottom right.

Changing the cursor's position allows your programs to quickly draw
interesting shapes and images! Run the program below for a simple example.

```
+-----------------+            
|@`10`sW1W+s`15`sv|            
|v`42`s+s`91`s+  <|            
|>s+s`31`s`37`s  v|            
|vs+s+s`74`s`34` <|            
|>+s+sH           |            
+-----------------+            
           v                   
           |>--------v         
           v^        |         
      +-------+      v         
      |       |     +=========+
      |  @>rsv|     :         :
      |v     <|     :         :
      |>`12`sv|>--->:         :
      |      1|     :         :
      |       |     :         :
      |      s|     :         :
      |   ^  <|     :         :
      +-------+     +=========+
             v       ^         
             >-------^         
```

## Further study

This wraps up our whirlwind tour of your computer's architecture. You are now
ready to begin your homework.

To get started, take a look at how problems are graded (`/grading`), and then
visit the problem sets page (`/problem-sets`) to try your first problem.

To clear up any ambiguities and view the full list of supported operations,
check out the language reference and instruction set (`/language-reference`).
For help with the editor, view the editor help page (`/editor-help`).

Whether you're a new student eager to write your first program or an
experienced practitioner who's ready to develop their own methods of creating
littleman programs, we're excited to see what you do!

## Definitions

- **tick** — The unit of time. Each tick, every little man executes the
  instruction he is standing on and then, if possible, takes one step in his
  current direction.
- **blocked** — A little man is blocked when the instruction he is standing on
  cannot complete yet (for example, receiving from an empty pipe). A blocked
  man stays where he is and tries again next tick.
- **instruction** — A single ASCII character that specifies an operation that
  a little man should perform.
- **error** — A fatal mistake — hitting a wall, stepping on an invalid
  instruction. An error immediately ends the whole program.
- **halt** — A halted little man stops moving and executing instructions. A
  halted program stops ticking.
- **direction** — The way a little man is currently facing — up, down, left,
  or right. Each tick he tries to step one square that way, unless he is
  blocked.
- **room** — A little man's home. A rectangular area drawn with + at the
  corners, - along the top and bottom walls, and | along the left and right
  walls.
- **.man** — The canonical file extension for little man programs.
- **hand** — Each little man has two hands. Each hand can hold a single
  integer.
- **main hand** — One of the little man's hands. Labeled 'A' in the littleman
  editor. Many operations, like running over a number or adding two numbers,
  change the value in a little man's main hand.
- **off hand** — The other of a little man's hands. Labeled 'B' in the
  littleman editor. Operations often use the value in a little man's off hand
  but rarely write to it.
- **pipe** — A unidirectional connection between two rooms. Values travel one
  pipe cell per tick; a pipe can hold as many values as it has cells.
- **io room** — The input room and the output room: special 3x3 rooms
  containing only the character I or O. Values read from the input room's pipe
  are the program's input; values sent into the output room's pipe are the
  program's output.
- **backpack** — A container each little man carries, capable of holding one
  integer. Shown as BP in the littleman editor. A little man cannot look at
  the value in his backpack, but he can turn based on it.
- **operation** — An instruction — see instruction.
- **program** — A grid of ASCII characters that one or more little men walk
  and execute.
- **pixel** — A solid block of color that is approximately as large as a
  little man.
- **display** — a rectangular device that can show images on command.
- **display cursor** — The position on a display where the next pixel will be
  drawn. The cursor advances from left to right and top to bottom as pixels
  are drawn.
- **display screen buffer** — One of a display's two stored images: current
  (the image shown on the display) and next (the image being composed). A swap
  copies next to current.

## Instruction summary (compiled from the text above)

| Char | Effect |
|------|--------|
| `@` | Little man (start position; begins moving right) |
| `H` | Halt |
| `^` `v` `<` `>` | Set direction up/down/left/right |
| `0`–`9` | Load digit into main hand (A) |
| `` `n` `` | Load multi-digit number into A (walkable any direction; spaces ignored) |
| `M` | Copy A → B (off hand) |
| `W` | Swap A ↔ B |
| `+` `-` `*` `/` `%` | Arithmetic A op B → A (division: floor → A, remainder → B) |
| `N` | Negate A |
| `&` `\|` `~` `{` `}` | Binary AND, OR, XOR, shift left, shift right |
| `s` | Send A to nearest outgoing pipe |
| `r` | Receive from nearest incoming pipe → A |
| `R` | Receive from any incoming pipe → A |
| `S` | Send A to every outgoing pipe |
| `U` | Like R, then turn away from the pipe received from |
| `X` | Turn on A: <0 left, >0 right, 0 straight |
| `b` | Copy A → backpack |
| `m` | Decrement backpack |
| `a` | Turn left if backpack > 0 |
| `d` | Turn right if backpack > 0 |
| `x` | Turn left if backpack even, right if odd |
| `]` | Backpack ← floor(backpack / 2) |
| `q` | Backpack ← count of values in nearest incoming pipe |
