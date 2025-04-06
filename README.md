# XML Preprocessor

_XML Preprocessor_ is a program that allows some extensions to the [Google-Samsung Watch Face Format XML schema](https://developer.android.com/training/wearables/wff/watch-face). It reduces the need to repeat values and XML elements, and it allows attribute values to be specified using meaningful names and equations.

Because it runs prior to the watchface being built, _XML Preprocessor_ can't provide any additional on-watch capabilities. This also means that it has no impact on watchface runtime performance, memory usage or battery life (unless you abuse _XML Preprocessor_'s ability to create multiple XML elements easily).

The preprocessor works by:

- reading an input file, which is a `watchface.xml` file with preprocessor extensions
- processing the extensions to create the specified XML elements and attribute values
- writing a standard WFF output file (typically `watchface.xml`).

This documentation assumes:

- familiarity with WFF
- familiarity with the process for building, installing and testing watchfaces using WFF (_eg_, [Google's instructions](https://developer.android.com/training/wearables/wff/setup) and [samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat))
- familiarity with Python
- the use of Microsoft Windows (although the preprocessor should work on any operating system).

#### Contents

- [Features](#features)
  - [`<Define>` Elements](#defines)
    - [`WFF Data Source Values`](#data-source-values)
    - [`Returning XML`](#returning-xml)
  - [`<Symbol>` and `<Use>` Elements](#symbol)
    - [Customising `<Use>` Instances with Top-level Attributes](#use_attrib)
    - [`<Transform>`](#transform)
    - [`<Delete>`](#delete)
    - [`<Symbol>` Candidate Selection](#candidates)
  - [`<If>` Elements](#if)
  - [`<Repeat>` Elements](#repeat)
  - [XML Element `{Expression}`s](#expressions)
  - [`<Import>` Elements](#import)
    - [`<Import>` XML](#import_xml)
    - [`<Import>` Python](#import_py)
  - [Example](#full_example)
- [Installation](#installation)
  - [Install with Clockwork](#install-clockwork)
  - [Manual Installation](#install-manual)
  - [lxml](#install-lxml)
- [Usage](#usage)
  - [Prepare Input File](#prepare)
  - [Run the Preprocessor](#run)
  - [Build and Test Watchface](#build)
  - [Debugging](#debugging)
    - [`pp_log()`](#pp_log)
- [Limitations](#limitations)
- [Change Log](#breaking)
- [Other Applications](#applications)
- [Similar Tools](#tools)

## <a id="features"></a>FEATURES

### <a id="defines"></a>`<Define>` Elements

`<Define>` elements can be used to contain Python code that defines variables and functions. Those variables and functions can then be used in other `<Define>` code and in [XML element `{expression}`s](#expressions).

#### Example

    <Define>
        GAUGE_DIAMETER = 200
        def centre(parent_size, self_size):
            # Return x or y to centre self within element.
            return round((parent_size - self_size) / 2)
    </Define>
    ...
    <Group
        width="{GAUGE_DIAMETER}"
        x="{centre(PARENT.width, SELF.width)}"
        ...

#### Notes

Everything between the opening and closing tags (`<Define>` and `</Define>`) must be Python variable and function definitions.

> [!WARNING]
> If you define a variable or function with the same name as a preprocessor or built-in Python variable or function, _Bad Things™_ will probably happen. Global variables and functions used internally by the preprocessor have names that start with `xmlpp`; you should also avoid redefining [pp_log()](#pp_log).

<a id="indentation"></a>Your Python code must comply with Python's indentation requirements. Within a `<Define>` element, you have these options:

- A single short definition can be included immediately between `<Define>` and `</Define>` on a single line.
- Left-align the first line of Python code, then maintain that indentation using Python conventions in subsequent lines.
- Indent the first line of Python code as you see fit (_eg_, to the right of the `<Define>` tag as in the example above), then maintain that indentation using Python conventions in subsequent lines.
- Blank lines are okay (regardless of indentation).

If you need to use functions that are defined in Python modules (_eg_, `math.sqrt()`), include the necessary `import` statement(s) in a `<Define>` element.

Comments can be included in `<Define>` code using normal Python conventions.

You can have multiple definitions in a single `<Define>` element; you can also use multiple `<Define>` elements.

The preprocessor executes code in `<Define>` elements in the order in which it appears in the input XML file. This means that symbols can be redefined throughout the file.

#### <a id="data-source-values"></a>WFF Data Source Values

[WFF data source values](https://developer.android.com/training/wearables/wff/common/attributes/source-type), which are equivalent to [Watch Face Studio tag values](https://developer.samsung.com/watch-face-studio/user-guide/tag-expression.html), aren't available until the watchface is running on a real watch or virtual device. Therefore, such values can't be used in `<Define>` elements because those are evaluated before the watchface is even built. However, there are a few ways to avoid repeating expressions involving data sources.

A string variable can contain the names of data sources; _eg_:

    myTagEquation = "[COMPLICATION.TITLE] != null &amp;&amp; [COMPLICATION.MONOCHROMATIC_IMAGE] == null"

This could then be used in an `{expression}` like this:

    <Expression name="symmetric">
        {myTagEquation}
    </Expression>

This can be useful if such blocks of code need to be repeated (in which case, consider using [`<Repeat>`](#repeat) or putting them in a [`<Symbol>`](#symbol)).

You can write Python functions that take data source names as parameters and return a string representation of an equation; _eg_:

    MY_CONSTANT = 4
    def myFunc(tagString, y):
        return '({tagString})*{y}'.format(tagString=tagString, y=y)

Such a function could be used in an `{expression}` like this:

    "{1 + MY_CONSTANT} + {myFunc('[SECOND] + 2', 3)}"

After preprocessing, the resulting string would be:

    "5 + ([SECOND] + 2)*3"

Note that embedding string literals (_eg_, `'[SECOND]'`) within attribute values may require cunning use of different types of quotation marks.

#### <a id="returning-xml"></a>Returning XML

Normally, functions within `<Define>` will return a string or string-compatible value that will be used within an XML attribute value. The `centre()` example (above) does this. However, if a function returns an [Element object](https://lxml.de/apidoc/lxml.etree.html#lxml.etree.Element), that element and/or its children will be inserted into the watchface.xml element tree in place of the `{expression}` that called it. Here's an example:

    <Define>
        def generateSquares(count, width, height):
            # Returns XML for a row of count squares, to fit within a PartDraw of width and height.
            xIncrement = (width - height) / (count - 1)
            # Because we want to return more than one top-level element, we must use Dummy root:
            root = xmlpp_ET.Element("Dummy")
            for i in range(count):
                rect = xmlpp_ET.SubElement(root, "Rectangle", {"x":f"{i*xIncrement}", "y":"0", "width":"20", "height":"20"})
                xmlpp_ET.SubElement(rect, "Fill", {"color":"#00FF00"})
            return root
    <Define>
    ...
    <PartDraw x="100" y="75" width="250" height="20">
        {generateSquares(5, SELF.width, SELF.height)}
    </PartDraw>

> [!Note]
> The most politically-correct way to create XML elements is probably to use `etree` methods as above. However, if you're uncomfortable with that, you can construct your XML as a string and convert it to an Element object when done. If you do this, you'll need to escape characters such as `<` and `>`. This version of the above example generates the same XML:

    def generateSquares(count, width, height):
        # Returns XML for a row of count squares, to fit within a PartDraw of width and height.
        xIncrement = (width - height) / (count - 1)
        # Because we want to return more than one top-level element, we must use Dummy root:
        xmlString = "&lt;Dummy&gt;"
        for i in range(count):
            xmlString += f'&lt;Rectangle x="{i*xIncrement}" y="0" width="{height}" height="{height}"&gt;&lt;Fill color="#FF0000"/&gt;&lt;/Rectangle&gt;'
        xmlString += "&lt;/Dummy&gt;"
        return xmlpp_ET.fromstring(xmlString)

Usage:

- You can use `xmlpp_ET` to access Python's [`lxml.etree`](https://lxml.de/apidoc/lxml.etree.html) module.

- The element returned by a Python function can be the root of a tree containing a hierarchy of sub-elements.

- <a id="dummy"></a>If you want to insert multiple elements at the top level, wrap them in a `<Dummy>` root element (as in the example above). The `<Dummy>` element itself won't be inserted, but all of its child elements will be. However, if the tag of the root element is _not_ `Dummy`, the root (and its child elements) will be inserted.

- XML elements can be inserted into an element's text (as above) or appended to its tail. The latter is achieved by putting the `{expression}` _after_ an element's closing tag, and has the effect of inserting the returned elements after the closing tag (_ie_, they will have the same parent).

- The `{expression}` that calls the element generation function must be the only content in the element's text or tail.

- XML elements can't be inserted into an attribute value, so don't call a function that returns an element from within an attribute value `{expression}`.

- If you only need to generate a sequence of similar elements, consider using [`<Repeat>`](#repeat) instead of a Python function.

> [!Note]
> The ability to generate XML from Python is not as useful as it might initially seem. As with everything that the preprocessor does, it happens prior to the watchface being built; it does not happen when the watchface is running.

> [!Caution]
> The ability to generate XML structures in loops makes it easy to create large numbers of elements, such as tick marks around a watch face index. However, this can result in runtime inefficiency. In general, it will be more efficient to use a single image to display multiple static items.

> [!Tip]
> The Python error `junk after document element` can occur if you attempt to create an XML tree with more than one root. Consider whether you should have used [`<Dummy>`](#dummy).

---

### <a id="symbol"></a>`<Symbol>` and `<Use>` Elements

You can employ `<Symbol>` elements to define a set of XML elements (including child elements) that can be inserted into `watchface.xml` more than once, via `<Use>` elements. This can improve the maintainability of your code by reducing duplication, like a function call in a programming language. Inserted `<Symbol>` elements can be tailored to their specific contexts in various ways (discussed later).

#### Example:

    <Symbol id="circle">
        <PartDraw
            height="{SMALL_SIZE}"
            width="{SELF.height}"
            x="100"
            y="0">
            <Ellipse
                height="{PARENT}"
                width="{PARENT}"
                x="0"
                y="0">
                <Fill color="{CIRCLE_FILL}" />
            </Ellipse>
        </PartDraw>
    </Symbol>
    ...
    <Use href="circle" />
    ...
    <Use href="circle" x="200" />
    ...

#### Notes

All `<Symbol>`s must have an `id` attribute. All `<Use>`s must have an `href` attribute, the value of which must match the `id` attribute of the `<Symbol>` to be inserted.

`<Use>` elements can be placed wherever the contents of the corresponding `<Symbol>` would be valid.

The `<Symbol>` element itself is not written to the output `watchface.xml` file. Only copies of the _contents_ of the `<Symbol>`, as specified by `<Use>` elements, are written.

A `<Symbol>` can contain more than one immediate child element. All such children (and their sub-elements) will be inserted when `<Use>`d.

A `<Symbol>` can contain one or more `<Use>` elements, which must refer to other `<Symbol>`s. In this way, `<Symbol>`s can be hierarchical.

A `<Symbol>` can't contain other `<Symbol>` elements (but see above). All `<Symbol>`s are considered to be global regardless of where they are declared; there is no way to limit a `<Symbol>`'s accessibility.

`<Symbol>`s can include [`{expression}`s](#expressions) which can, in turn, include variables and functions defined in [`<Define>`](#defines) elements. The example above contains several of these (although the `<Define>` element is not shown).

`<Symbol>` and `<Use>` can reduce the size of, and duplication in, your source file, but they won't do so for your `watchface.xml` file (which is used on the watch). This is because the preprocessor applies `<Symbol>` and `<Use>` elements _before_ the watchface build process happens. It has to be this way because WFF does not support `<Symbol>` and `<Use>`.

While `<Use>` can be employed to insert multiple copies of elements sequentially, the same effect can often be achieved more easily using [`<Repeat>`](#repeat). Bear this in mind if you're tempted to employ sequential `<Use>` elements for the same `<Symbol>`.

#### <a id="use_attrib"></a>Customising `<Use>` Instances with Top-level Attributes

`<Symbol>` and `<Use>` allow you to reuse similar elements without copying and pasting. However, you will often want to make minor adjustments to each instance; _eg_, specifying different `x` and `y` values. There are a few ways to achieve this.

If you specify attribute values in a `<Use>` element, those values (except for that of `href`) will be applied to _all_ of the top-level elements in the `<Symbol>` when it is inserted. The example above employs this feature: the second `<Use>` element overrides the value of the `<Symbol>`'s `x` attribute, so the second circle will have a different `x` value to that of the first circle.

Attribute values specified in a `<Use>` element do not change the `<Symbol>`; they're only applied to the _copy_ of the `<Symbol>` that's inserted in place of the `<Use>`. Subsequent `<Use>`s of the same `<Symbol>` will not include attribute values specified in prior `<Use>`s.

> [!WARNING]
> [`{expression}`s](#expressions) in attribute values are processed in the order in which the attributes appear in their element. Therefore, make sure you declare attributes with dependent values _after_ those on which they depend. WFF doesn't care about the order on which attributes are declared. Setting a bogus default value in a `<Symbol>` is okay if the actual value will be supplied by a `<Use>` element. Adding attributes via `<Use>` after the element has been declared will put the new attributes _after_ the predeclared attributes, so the new attribute's values won't be accessible by attributes declared earlier. So, this won't work:

        <Symbol id="icon">
            <PartImage
                width="{SELF.height}"
                ...
            </PartImage>
        </Symbol>
        <Use href="icon" height="{MY_SIZE}" />

> ...because `height` will be added to the `<PartImage>`'s attributes _after_ `width`, so `SELF.height` isn't known when processing the `width` `{expression}`. However, this _will_ work:

        <Symbol id="icon">
            <PartImage
                height="0"
                width="{SELF.height}"
                ...
            </PartImage>
        </Symbol>
        <Use href="icon" height="{MY_SIZE}" />

Attributes with names that start with `data-` (_eg_, `data-gauge-diameter`) will be deleted at the end of preprocessing. This can be useful for attributes that will be used internally by the `<Use>` instance (_eg_, `{PARENT.data-gauge-diameter}`) but which are not valid in WFF.

> [!WARNING]
> if you employ `data-` attributes in expressions, bear in mind that minus signs can be confused with hyphens in attribute names; _eg_, `PARENT.data-gauge-diameter-10`. If you intend to subtract, put a space before the minus sign; _eg_, `PARENT.data-gauge-diameter - 10`.

> [!TIP]
> Within `<Symbol>` definitions, you can initialise attribute values (including those in sub-elements) to default values. This way, you don't need to specify them when the `<Symbol>` is `<Use>`d and the defaults are appropriate. You only need to specify attribute values in `<Use>` when the values specified within the `<Symbol>` need to be changed.

#### <a id="transform"></a>`<Transform>`

A more flexible way to customise `<Symbol>` attribute values is to include one or more `<Transform>` elements within the relevant `<Use>`; _eg_: if your `<Symbol>` is:

    <Symbol id="myArc">
        <PartDraw...
           <Arc...
              direction="CLOCKWISE"
              ...
            </Arc>
        </PartDraw>
    </Symbol>

...and you want to make use of it but with `direction="ANTICLOCKWISE"`, do this:

    <Use href="myArc">
        <Transform
            href="PartDraw/Arc"
            target="direction"
            value="ANTICLOCKWISE" />
    </Use>

<a id="xpath"></a>The `href` attribute of the `<Transform>` element can accept any [`XPath`](https://en.wikipedia.org/wiki/XPath) expression supported by Python's [`lxml.etree`](https://lxml.de/xpathxslt.html#xpath) implementation; _eg_:

- `"PartDraw"` matches all `<PartDraw>` elements that are direct children of the `<Symbol>`

- `"PartDraw/Arc"` matches all `<Arc>` elements that are direct children of `<PartDraw>` elements that are direct children of the `<Symbol>`

- `"PartDraw[2]"` matches the second `<PartDraw>` element that is direct child of the `<Symbol>`

- `".//Arc"` matches all `<Arc>` elements anywhere in the `<Symbol>`

- `".//*[@direction='CLOCKWISE']"` matches elements of any type that have an attribute named `direction` with a value of `CLOCKWISE`.

> [!WARNING]
> `<Transform>` elements will be applied to _all_ elements in the `<Symbol>` that match the `href` value, and not just the first match. Be sure that `href` selects only the element(s) that you want to change.

Attribute value changes specified in a `<Use> <Transform>` element don't change the `<Symbol>`; they're only applied to the _copy_ of the `<Symbol>` that's inserted in place of the `<Use>`. Subsequent `<Use>`s of the same `<Symbol>` will not include attribute value changes specified in prior `<Use> <Transform>`s.

The preprocessor's `<Transform>` element is not the same as WFF's `<Transform>` element. The preprocessor's `<Transform>` element can only appear within a `<Use>` element, takes effect when the preprocessor is executed (as opposed to when the watchface is running), and requires a `href` attribute.

You can usually achieve the same effect as `<Transform>` by [setting attribute values directly in the `<Use>` element](#use_attrib), and copying them internally within the `<Symbol>` with [`PARENT`](#self_parent) or [`SELF`](#self_parent). This can be more concise if you need to set multiple attributes to the same (or a related) value. Remember that attributes that aren't valid WFF for the top-level elements in the `<Symbol>` should have names that start with `data-` so they'll be deleted after preprocessing.

#### <a id="delete"></a>`<Delete>`

`<Delete>` is similar to `<Transform>`, except that it simply removes elements (including their children) from the `<Symbol>` that match its `href` attribute value. `href` can take [XPath expressions](#xpath).

> [!WARNING]
> `<Delete>` elements will be applied to _all_ elements in the `<Symbol>` that match their `href` values, and not just the first match. Be sure that `href` selects only the element(s) that you want to delete.

Elements that are deleted by a `<Use> <Delete>` element do not change the `<Symbol>`; they're only applied to the _copy_ of the `<Symbol>` that's inserted in place of the `<Use>`. Subsequent `<Use>`s of the same `<Symbol>` will still contain elements that were deleted in prior `<Use> <Delete>`s.

Because you can delete elements from a `<Symbol>` when you `<Use>` it, but you can't add new elements, you should include all possibly-relevant elements in your `<Symbol>`s.

#### <a id="candidates"></a>`<Symbol>` Candidate Selection

Most IDEs and code editors can highlight differences between two documents. This can be a useful way of assessing whether two blocks of code have enough similarities to justify converting them to a `<Symbol>`, and it can show what `<Transform>`s and `<Delete>`s are necessary to adapt the `<Symbol>` to each `<Use>` instance. You may need to copy each code block into a separate document to facilitate comparison.

---

### <a id="if"></a>`<If>` Elements

`<If>` elements can be used to conditionally include XML elements. This can be useful for:

* debugging elements; _eg_, displaying diagnostic text

* hard-coded values to be displayed in screenshots

* hard-coded values for assessing Always On Display (AOD) (ambient) mode compliance; _eg_, lengthy strings.

> [!Tip]
> [Watch Face Format Always On Display Assessor](https://github.com/gondwanasoft/wff-aod) can be used to assess AOD compliance.

#### Usage

`<If>` requires an attribute named `condition`. The value of `condition` should be an [`{expression}`](#expressions). If `condition` evaluates to `True`, all of the `<if>` element's child elements will be retained; otherwise, they will be discarded.

In general, the `condition {expression}` will refer to one or more Python variables that have been defined in a previous [`<Define>` element](#defines).

#### Example

    <If condition="{DEBUG==1}">
        <PartDraw...>
            ...
        </PartDraw>
        <PartText...>
            ...
        </PartText>
    </If>

#### Notes

The `<If>` element itself is never retained. Only its child elements may be retained, depending on the value of the `condition` attribute.

The `condition` expression is evaluated when the preprocessor runs. Therefore, it can't depend on values that are only available when the watchface is running, such as [WFF data source values](https://developer.android.com/training/wearables/wff/common/attributes/source-type). However, child elements within the `<If>` _can_ refer to such values, since those elements may be parsed when the watchface is running. This can be useful for displaying complication data that might otherwise not be visible.

You can nest `<If>`s within `<If>`s.

Instead of using `<If>`, you can often use XML comment tags (`<!-- -->`) to 'comment out' XML elements. However, this won't work if there are comments within those elements because XML doesn't support nested comments. In addition, if you use `<If>`, you can make your code more readable by using `condition`s such as `"{SCREENSHOT}"`.

You can emulate Python's `elif` and `else` using sequential `<If>` elements with appropriate `condition` expressions.

Python's `if` and `match` statements are more powerful than the simplistic implementation here. If you need the greater flexibility of Python, you can call a Python function in a `<Define>` that performs the conditional test and [returns the XML elements to include](#returning-xml). A disadvantage of this approach is that you need to construct the XML elements using Python code.

---

### <a id="repeat"></a>`<Repeat>` Elements

You can use `<Repeat>` to create multiple sequential copies of its child elements.

#### Example

    <Repeat for="n" in="range(3)">
        <Line startX="{n*10}" .../>
        <Arc .../>
    </Repeat>

The preprocessor executes a Python [`for`](https://docs.python.org/3/reference/compound_stmts.html#for) statement using the `for` and `in` attribute values. For every iteration of that loop, it inserts a copy of the elements within the `<Repeat>`.

The Python variable name specified in the `for` attribute is available to the repeated elements. In the above example, it is used to specify a different `startX` for every `<Line>`.

The output resulting from this example is:

        <Line startX="0" .../>
        <Arc .../>
        <Line startX="10" .../>
        <Arc .../>
        <Line startX="20" .../>
        <Arc .../>

#### Notes

The `<Repeat>` element itself is not copied to the output file; only its children are.

The `in` attribute can be any valid Python [`range`](https://docs.python.org/3/library/stdtypes.html#range) expression, so it can also specify starting and increment (step) values.

The `in` attribute can use Python symbols defined in [`<Define>`](#defines) elements.

`<Repeat>` elements can be nested; _eg_:

    <Repeat for="x" in="range(0, 30, 10)">
        <Repeat for="y" in="range(0, 50, 10)">
            <Line startX="{x}" startY="{y}" .../>
        </Repeat>
    </Repeat>

`<Repeat>` is well-suited to creating multiple similar sets of elements in sequence. However, if you need to create similar sets of elements elsewhere (_ie_, not in sequence), [`<Use>`](#symbol) may be more appropriate.

If you need more flexibility in the creation of repeated elements than is possible with `<Repeat>`, you can [generate sequences of XML elements using Python code](#returning-xml).

> [!WARNING]

> In theory, any valid [Python `in` expression](https://docs.python.org/3/reference/compound_stmts.html#for) should work. However, only `range` has been tested.

> [!WARNING]

> `<Repeat>` makes it easy to generate a large number of XML elements. Each generated element must be processed by the watch when the watchface is running, with consequent impact on performance, memory and battery usage. Therefore, `<Repeat>` (and especially nested `<Repeat>`s) should be used judiciously. For example, even though `<Repeat>` could be used to create 60 tick marks around an index, it would probably be more efficient to use a single `<Image>` for this (and for static content in general).

>[!TIP]
>The preprocessor expands `<Repeat>` elements into an intermediate form for subsequent processing. In the case of the example above, this form is:

        <Define>n=0</Define>
        <Line startX="{n*10}" .../>
        <Arc .../>
        <Define>n=1</Define>
        <Line startX="{n*10}" .../>
        <Arc .../>
        <Define>n=2</Define>
        <Line startX="{n*10}" .../>
        <Arc .../>

---

### <a id="expressions"></a>XML Element `{Expression}`s

In some places, text enclosed in curly brackets `{ }` will be executed as a Python expression, and the resulting value will replace the bracketted text.

#### Example

    <PartDraw
        x = "{100+200}"
        ...

#### Notes

`{expression}`s will be executed and replaced in the following contexts:

- XML attribute values (as in the example above)

- XML element text (_eg_, within WFF [`<Template>`](https://developer.android.com/training/wearables/wff/group/part/text/formatter/template) elements)

- XML element tail (rarely/never used in WFF).

An attribute value string can contain normal text as well as an `{expression}`; _eg_:

    <Group name="complic{PARENT.slotId}" ...

An attribute value string can contain more than one `{expression}`; _eg_:

    "foo {expression1} bar {expression2} baz"

Everything between the opening and closing curly brackets must be a Python expression.

`{expression}`s can't contain line breaks (_ie_, the whole expression must be on one line).

`{expression}`s can use variables and functions that have been declared in [`<Define>`](#defines) elements, as well as any standard Python functions. If you need to use functions that are defined in Python modules (_eg_, `math.sqrt()`), include the necessary `import` statement(s) in a [`<Define>`](#defines) element.

If an `{expression}` calls a function that returns an XML element, that element and/or its sub-elements will be inserted in place of the `{expression}`. For details, see [here](#returning-xml).

Mathematical expressions in `<Define>` or `{expression}` can result in non-integer values, but some WFF attributes (_eg_, `x`) require integers. Use Python's `round()` function in such expressions.

<a id="self_parent"></a>Two special variables can be used within `{expression}`s:

- `SELF` refers to the current element. This can be used to access attribute values that have been previously defined in the current element; _eg_, `width="{SELF.height * 2}"`.

- `PARENT` refers to the parent of the current element. If the required attribute hasn't been defined on the parent element, `PARENT` will consider the parent's parent, and so on up the XML tree. `PARENT` can be used in two ways:

  - `PARENT.attributeName` returns the parent's value of the named attribute.

  - `PARENT` without an attribute name returns the parent's value of the attribute that is currently being defined; _eg_, `width="{PARENT}"` will set the current element's width to the same value as that of its parent.

[WFF data source values](https://developer.android.com/training/wearables/wff/common/attributes/source-type), which are equivalent to [Watch Face Studio tag values](https://developer.samsung.com/watch-face-studio/user-guide/tag-expression.html), aren't available until the watchface is running on a real watch (or virtual device). Therefore, such values can't be used in preprocessor `{expression}`s because `{expression}`s are evaluated before the watchface is even built. However, it is possible to use data source _names_ in `{expression}`s. For example, the XML code to display a `<PartImage>` for an `AMBIENT` (AOD) icon is almost identical to that for a non-AMBIENT icon. The only difference will often be that one `<PartImage>` will use a `[COMPLICATION.MONOCHROMATIC_IMAGE_AMBIENT]` whereas the other will use a `[COMPLICATION.MONOCHROMATIC_IMAGE]`. You can write a `<Symbol id="iconVariant">` to handle both cases. The code within the `<Symbol>` could specify `[COMPLICATION.MONOCHROMATIC_IMAGE]` so that `<Use href="iconVariant"/>` would display it. When the `AMBIENT` variant needs to be displayed instead, the `<Symbol>` could be `<Use>`d again but with the data source value changed; _eg_:

    <Use href="iconVariant">
        <Transform
            href=".//Image"
            target="resource"
            value="[COMPLICATION.MONOCHROMATIC_IMAGE_AMBIENT]" />
    </Use>

(In a full implementation, you would also need to transform `alpha` and `<Variant>` to ensure that only one image is displayed.)

---

### <a id="import"></a>`<Import>` Elements

`<Import>` elements let you merge XML or Python code from separate files into your main input file.

Notes:

- An `<Import>`ed file can contain `<Import>` elements.
- In addition to the filename, a path (directory/folder) can be included in `href`.
- `href` paths are relative to the directory of the file containing the `<Import>` element.

> [!WARNING]
> `<Import>` doesn't provide namespacing, local scoping, _etc_. All imported elements and code are global. Be careful using broad names such as `COMPLICATION_WIDTH` because such names would clash if used independently elsewhere. For maximum safety, consider prefixing names with a unique informal namespace; _eg_, `RECT_RANGED_COMPLIC_WIDTH`.

#### <a id="import_xml"></a>`<Import>` XML

Usage:

    <Import href="filename.xml" />

This will replace the `<Import`> element with XML elements contained in `filename.xml`.

The XML in `filename.xml` must be valid, meaning that it can only have one root element. If you only want to import one element and its sub-elements, you don't need to do anything special. However, if you want to import more than one top-level element, make those elements children of a `<Dummy>` root element. The `<Dummy>` element itself won't be imported, but its sub-elements will be. For example, if `my_component.xml` contained this:

    <Dummy>
        <PartDraw... />
        <PartText... />
    </Dummy>

...then `<Import href="my_component.xml" />` would be replaced with this:

    <PartDraw... />
    <PartText... />

`<Import>` can be employed to reuse [`<Symbol>`](#symbol)s across projects. In this case, the imported file will typically contain a [`<Symbol>`](#symbol) element. The imported `<Symbol>` can then be accessed by `<Use>` elements. It will normally be necessary to customise the imported `<Symbol>`. As with `<Symbol>`s contained in the input file, imported `<Symbol>`s can be customised using [top-level attributes](#use_attrib) (including `data-` attributes), [`<Transform>`](#transform) and [`<Delete>`](#delete). In addition, imported `<Symbol>`s can use variables and functions from [`<Define>`](#defines) elements declared in the context into which they are imported.

#### <a id="import_py"></a>`<Import>` Python

Usage:

    <Import href="filename.py" />

This will replace the `<Import`> element with a [`<Define>`](#defines) element that contains the contents of `filename.py`. For example, if `my_code.py` contained this:

    COMPLICATION_DIAMETER = 100
    def centre(parent_size, self_size): return round((parent_size-self_size)/2)

...then `<Import href="my_code.py" />` would be replaced with this:

    <Define>
        COMPLICATION_DIAMETER = 100
        def centre(parent_size, self_size): return round((parent_size-self_size)/2)
    </Define>

Importing Python from a `.py` file has these advantages:

- common constants and functions can be reused
- coding assistance can be obtained by editing `.py` files in a suitable IDE or code editor.

If the preprocessor's `<Import>` element is inadequate, you can use Python's native `import` capabilities within a `<Define>` element.

---

### <a id="full_example"></a>Example

A complete example of a preprocessor input file is [here](example/watchface/watchface-pp.xml). It imports [ranged-complic.xml](example/watchface/widgets/ranged-complic/ranged-complic.xml) and [defines.py](example/watchface/widgets/ranged-complic/defines.py). The corresponding `watchface.xml` produced by the preprocessor is [here](example/watchface/src/main/res/raw/watchface.xml).

> [!NOTE]
>
> - This example attempts to demonstrate all of the preprocessor's capabilities; it is not a sensible way to structure an actual project.
> - The input files are larger than the output file. This is not normally the case because extensive `<Use>` elements reduce duplication. Moreover, the input file can be easier to develop and maintain because it avoids duplication and allows meaningfully-named variables and functions.

## <a id="installation"></a>INSTALLATION

### <a id="install-clockwork"></a>Install with [Clockwork](https://clockwork-pkg.pages.dev/)

`Clockwork` is the easiest way to manage the dependencies of your Watch Face Format project. It can also validate, build and install watchfaces. If you don't have it yet, learn all about it at [clockwork-pkg.pages.dev](https://clockwork-pkg.pages.dev/install).

```shell
clockwork add xml-preprocessor
```

If Clockwork can't find a compatible version of Python when [building](https://clockwork-pkg.pages.dev/guides/creating), it will automatically try to install Python.

### <a id="install-manual"></a>Manual Installation

Install a relatively recent version of [Python](https://www.python.org/) (_eg_, 3.13+).

Put `preprocess.py` somewhere where you can conveniently access it from your watchface project. For example, if you use the same file structure as Google's [samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat), you could put `preprocess.py` in the same folder as `gradlew`.

> [!IMPORTANT]
> If your project already contains a `watchface\src\main\res\raw\watchface.xml` file (and it probably does), **_COPY THIS FILE TO SOMEWHERE SAFE_** because you will probably use the preprocessor to overwrite it.

### <a id="install-lxml"></a>lxml

When first run, the preprocessor will try to install Python's `lxml` module if necessary. If it fails (_eg_, because `pip` can't be found), you will need to do this manually:

    pip install lxml

## <a id="usage"></a>USAGE

### <a id="prepare"></a>Prepare Input File

Obtain, create or edit an XML file (suggested name: `watchface-pp.xml`) that contains WFF code and any preprocessor features that you want to use. You can save this anywhere; your project's `watchface` subfolder is recommended.

> [!TIP]
> For an initial test, you don't have to use any preprocessor features; you can copy a standard `watchface.xml` file.

> [!TIP]
> Some lazy ways to obtain an initial file are:
>
> - [Google's samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat)
> - `watchface.xml` extracted from a [Samsung Watch Face Studio (WFS)](https://developer.samsung.com/watch-face-studio/overview.html) project:
>   - 'Publish' the project in WFS.
>   - Find the resulting `.aab` file in `build\[project]`.
>   - Append `.zip` to the `.aab` file's name.
>   - Copy `base\res\raw\watchface.xml` from within the `.aab.zip` file.
>   - Restore the `.aab` file's name by removing the `.zip`.
> - [Empty WFF boilerplate project](https://github.com/gondwanasoft/wff-boilerplate).

> [!TIP]
> To avoid confusion, name your preprocessor input file something other than `watchface.xml`; _eg_, `watchface-pp.xml`.

> [!TIP]
> [WFS](https://developer.samsung.com/watch-face-studio/overview.html) sometimes uses XML `CDATA` strings in `watchface.xml` files it creates. The XML parser used by the preprocessor converts `CDATA` strings into escaped XML; _eg_: `"<![CDATA[...&&...]]>"` becomes `"...&amp;&amp;..."`. The watchface build process is happy with this. You may find the need to use escaped XML characters in other situations, such as `&gt;` in place of `>` in element text.

### <a id="run"></a>Run the Preprocessor

From a command prompt, execute `preprocess.py`, passing the input filename and output filename as parameters; _eg_:

    preprocess.py watchface\watchface-pp.xml watchface\src\main\res\raw\watchface.xml

If there were no errors, the output file will have been created. If you like, you can look at it in a text/code editor to see the code generated by the preprocessor.

> <a id="ugly"></a>

> [!TIP]
> The formatting of the XML file generated by the preprocessor can be ugly. To make the file easier to understand, format/prettify/beautify it using an IDE, code editor or other app.

`preprocess.py` will normally refuse to write the output file if doing so would overwrite an extant file. To allow it to overwrite, add the `-y` command line parameter.

> [!TIP]
> [Clockwork](#install-clockwork) can call `preprocess.py` as part of its build process. Alternatively, if you use Microsoft Windows, [wff-build-script](https://github.com/gondwanasoft/wff-build-script) can also run the preprocessor, validate, build and install your watch face.

### <a id="build"></a>Build and Test Watchface

Use the output file (typically `watchface.xml`) to build and test the watchface as you normally would (_eg_, see [Google's instructions](https://developer.android.com/training/wearables/wff/setup) and [samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat)).

### <a id="debugging"></a>Debugging

If the preprocessor can't process the input file, it will either display an error message or throw an uncaught exception. In either case, the console output should help you to identify the problem.

> [!WARNING]
> On error, the preprocessor will often report a line number for the error in the original source file. Line numbers are only approximate; in some cases, they can be very misleading. If the erronous element was generated internally by the preprocessor, the line number will be 'None'.

> [!NOTE]
> Processing stops as soon as one error is encountered. There could be multiple errors in the input file, so you need to keep correcting errors and rerunning the preprocessor until it completes successfully.

If the error message doesn't help, examine the output file to see how it differs from what you wanted.

For additional information, you can run `preprocess.py` again but with the `-d` command line parameter added. This will save a log of the preprocessor's activities and intermediate results to `debug-pp.txt`. The state of the XML document at the time of the error is saved to `debug-pp.xml` (unless the error occurred during initial XML loading).

Most types of error will be flagged in `debug-pp.xml` by adding an attribute named `xmlpp-error` to the offending element. This isn't possible where the offending element has been removed prior to the error being detected (_eg_, `<Delete href="not-found">`). The actual source of the error could be well below the `xmlpp-error` attribute; it could even be in the element's tail (_ie_, the text between its end-tag and next element's start-tag).

Even if the preprocessor completes successfully, it's eminently possible for the output file to be rejected by the watchface build process (`gradle`), or for the resulting watchface to look wrong or behave unexpectedly. Examine the output file and/or use `-d` to work out why.

> <a id="validator"></a>

> [!TIP]
> If you get errors when you attempt to build the watchface, use the [Format validator](https://github.com/google/watchface/tree/main/third_party/wff) to check your `watchface.xml`. Ideally, you always do this before you attempt to build the watchface, since it can provide much more useful error messages than the build process. Be aware that line numbers (_etc_) reported by the validator refer to `watchface.xml` rather than the preprocessor's input file (_eg_, `watchface-pp.xml`).

> [!TIP]
> Many WFF elements can be given a `name` attribute. Using unique values for `name`s can help you to match elements between your `watchface-pp.xml` and `watchface.xml` files. This can be especially useful since comments in the input file are not included in the output file. Be aware that, if you employ `<Use>` more than once for a particular `<Symbol>`, elements within the `<Symbol>` will be repeated in `watchface.xml` so `name` attributes will no longer be unique.

> [!TIP]
> You can use XML elements in an [`<If>`](#if) to display debugging information on the watch face while it is running, without having to delete or comment out such elements when building a production release. This can be useful to see the values of [`WFF Data Source Values`](#data-source-values), or values derived from them, since those values aren't available when the preprocessor runs.

#### <a id="pp_log"></a>`pp-log()`

The preprocessor provides a `pp_log()` function that can be called within `watchface-pp.xml` [`<Define>`](#defines) functions and attribute value [`{expression}`](#expressions)s. It prints the value and type of its first argument to the console when `preprocess.py` is executed. Use it like this:

    pp_log(expression[, prompt])

- `expression`: Python code for the value that you want to display.
- `prompt`: an optional prompt to print before the value of the expression.

You can use `pp_log()` in a `<Define>` element like this:

    <Define>
        def centre(parent_size, self_size):
            pp_log(parent_size/2, "centre() parent_size halved:")
            ...
    </Define>

You can use `pp_log()` in an attribute value `{expression}` like this:

    centerY="{pp_log(PARENT+20, 'My center Y')}"

This works because `pp_log()` returns the value of its first argument; so, if the parent element's centerY were 100, the resulting WFF XML would be:

    centerY="120"

Note that you can use `{expression}`-specific features (such as `PARENT`) in `pp_log()` when it is called from within an attribute value `{expression}`.

> [!TIP]
> You may need to employ a variety of types of quotation marks when embedding a call to `pp_log()` in an attribute value string.

## <a id="limitations"></a>LIMITATIONS

The preprocessor uses two insecure Python functions ([`exec()`](https://docs.python.org/3/library/functions.html#exec) and [`eval()`](https://docs.python.org/3/library/functions.html#eval)). It makes no attempt to ameliorate the risks associated with these. You should only use the preprocessor on input files that you trust.

The preprocessor will catch and report some error conditions nicely. However, many error conditions will not be caught and will result in the preprocessor throwing Python exceptions.

The preprocessor doesn't check whether the file it creates is valid WFF XML (see this [tip](#validator)).

Python code in `<Define>` elements is global, rather than being encapsulated within the scope in which it is declared.

`<Symbol>`s are global, rather than being encapsulated within the scopes in which they are declared.

[Indentation](#indentation) of Python code in `<Define>` elements is rudimentary. Using `Tab` characters is especially risky; stick to `space`s.

IDEs and code editors are unlikely to provide coding assistance for Python code in `<Define>` elements or `{expression}`s. This is because such code is considered to be XML element text or attribute value strings; only the preprocessor knows otherwise. A partial workaround is to use [`<Import>`](#import_py).

> [!TIP]
> If you're desperate for Python coding help, put the Python code in a `.py` file and open it in a Python development environment.

`watchface-pp.xml` or `watchface.xml` files used by the preprocessor can't be imported into [Samsung's Watch Face Studio](https://developer.samsung.com/watch-face-studio/overview.html) because that app doesn't support importing XML.

The formatting of the XML file generated by the preprocessor can be ugly (see this [tip](#ugly)).

XML comments in the input file are not included in the output file.

## <a id="breaking"></a>CHANGE LOG

_This section describes major changes only; see [github](https://github.com/gondwanasoft/xml-preprocessor/commits/main/) for more._

#### Version 1.3.0

Prior to v1.3.0, [`<Import>`ed XML elements](#import_xml) always needed a `<Widget>` root element, which was discarded. From v1.3.0, the root element is only discarded if it is `<Dummy>`. If you only need to `<Import>` a single element (typically `<Symbol>`), you don't need to put it inside any other root element.

This change was made for consistency with the use of [Python functions that return XML](returning-xml). Such functions won't always return widgets (components). Moreover, since most `<Import>` files will only contain a `<Symbol>`, the need to wrap it within another element to ensure a single root was redundant.

#### Version 2.0.0

The Python `lxml` module is now used for XML parsing and manipulation. This may result in some breaking changes and new bugs, although backward compatibility has been tested fairly thoroughly.

[`<Define>`](#defines) elements can now be used in child elements at any level (_ie_, they no longer need to have the root element as their immediate parent).

Code in [`<Define>`](#defines) elements is now executed in the order in which it appears in the XML file, in conjunction with [{expression}](#expressions) evaluation. Previously, all `<Define>` code was executed before evaluating any `{expression}`s.

[`<Symbol>`](#symbol) elements can now be used in child elements at any level (_ie_, they no longer need to have the root element as their immediate parent).

[`<Repeat>`](#repeat) element has been added.

Empty [`{expression}`s](#expressions); _ie_, those that become `{}` after variable substitution, are now simply removed. Previously, the empty expression was passed to Python for evaluation, which never ended well.

A bug has been fixed when evaluating an `{expression}` that returned an empty string; eg, `{"   ".strip()}`. Previously, this would result in the `{expression}` (Python code and braces) being copied into the output XML file.

When an error occurs, the preprocessor now displays the reported line number of the error in the original source file. If the erronous element was generated internally by the preprocessor, the line number will be 'None'. Line numbers are only approximate; in some cases, they can be very misleading.

When executed with the `-d` (debug) command-line option, the log is now saved to `debug-pp.txt` instead of being displayed on the console. The state of the XML document at the time of the error is now saved to `debug-pp.xml` (unless the error occurred during initial XML loading).

Most types of error will now be flagged in `debug-pp.xml` by adding an attribute named `xmlpp-error` to the offending element. This isn't possible where the offending element has been removed prior to the error being detected (_eg_, `<Delete href="not-found">`). The actual source of the error could be well below the `xmlpp-error` attribute; it could even be in the element's tail (_ie_, the text between its end-tag and next element's start-tag).

#### Version 2.1.0

[`<If>`](#if) element has been added.

## <a id="applications"></a>OTHER APPLICATIONS

Although `preprocessor.py` was written specifically to help with WFF XML, the approach is fairly general. As a result, it should work in many other situations in which XML file generation can benefit from its features. Possible issues include:

- XML element tags used by the preprocessor (`<Define>`, _etc_) may clash with those of the XML schema being used.
- The use of curly brackets `{ }` to embed expressions may clash with other uses of such brackets.
- The formatting of the output file will rarely match that of the input file.
- XML `<!--comments-->` will not appear in the output file.
- `CDATA` strings and escape characters (`&amp;`, _etc_) may be changed.

## <a id="tools"></a>SIMILAR TOOLS

### <a id="xinclude"></a>XInclude

[XInclude](https://en.wikipedia.org/wiki/XInclude) can be used in some contexts to do similar things to preprocessor's [`<Import>`](#import).

### <a id="xslt"></a>XSLT

XSLT is a more powerful tool for generating XML. It doesn't rely on custom XML elements and attribute values, but uses a separate `.xslt` file to describe the transformations required. If your need is primarily data/format transformation, XSLT is superior.

### <a id="peitaosu"></a>peitaosu/XML-Preprocessor

[peitaosu/XML-Preprocessor](https://github.com/peitaosu/XML-Preprocessor/tree/master) is a repo that contains some equivalent features, such as `include` ([`<Import>`](#import)) and iteration ([`<Repeat>`](#repeat)).


