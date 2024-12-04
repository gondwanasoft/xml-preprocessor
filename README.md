# XML Preprocessor

_XML Preprocessor_ is a program that allows some extensions to the [Google-Samsung Watch Face Format XML schema](https://developer.android.com/training/wearables/wff/watch-face). It reduces the need to repeat values and XML elements, and it allows attribute values to be specified using meaningful names and equations.

Because it runs prior to the watchface being built, _XML Preprocessor_ can't provide any additional on-watch capabilities. This also means that it has no impact on watchface runtime performance, memory usage or battery life.

The preprocessor works by:
* reading an input file, which is a `watchface.xml` file with preprocessor extensions
* processing the extensions to create the specified XML elements and attribute values
* writing a standard WFF output file (typically `watchface.xml`).

This documentation assumes:

* familiarity with WFF
* familiarity with the process for building, installing and testing watchfaces using WFF  (*eg*, [Google's instructions](https://developer.android.com/training/wearables/wff/setup) and [samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat))
* familiarity with Python
* the use of Microsoft Windows (although the preprocessor should work on any operating system).

#### Contents

* [Features](#features)
  * [`<Define>` Elements](#defines)
  * [`<Symbol>` and `<Use>` Elements](#symbol)
    * [Customising `<Use>` Instances with Top-level Attributes](#use_attrib)
    * [`<Transform>`](#transform)
    * [`<Delete>`](#delete)
    * [`<Symbol>` Candidate Selection](#candidates)
  * [XML Element `{Expression}`s](#expressions)
  * [Example](#full_example)
* [Installation](#installation)
* [Usage](#usage)
  * [Prepare Input File](#prepare)
  * [Run the Preprocessor](#run)
  * [Build and Test Watchface](#build)
  * [Debugging](#debugging)
    * [`pp_log()`](#pp_log)
* [Limitations](#limitations)
* [Other Applications](#applications)

## <a id="features"></a>FEATURES

### <a id="defines"></a>`<Define>` Elements

`<Define>` elements can be used to contain Python code that defines variables and functions. Those variables and functions can then be used in other `<Define>` code and in [XML element `{expression}`s](#expressions).

#### Example:

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

All `<Define>` elements must be direct children of the `<Watchface>` element.

Everything between the opening and closing tags (`<Define>` and `</Define>`) must be Python variable and function definitions.

> **WARNING:** If you define a variable or function with the same name as a preprocessor or built-in Python variable or function, *Bad Things™* will probably happen. Global variables and functions used internally by the preprocessor have names that start with `xmlpp`; you should also avoid redefining [pp_log()](#pp_log).

<a id="indentation"></a>Your Python code must comply with Python's indentation requirements. Within a `<Define>` element, you have these options:

* A single short definition can be included immediately between `<Define>` and `</Define>` on a single line.
* Left-align the first line of Python code, then maintain that indentation using Python conventions in subsequent lines.
* Indent the first line of Python code as you see fit (*eg*, to the right of the `<Define>` tag as in the example above), then maintain that indentation using Python conventions in subsequent lines.
* Blank lines are okay (regardless of indentation).

If you need to use functions that are defined in Python modules (*eg*, `math.sqrt()`), include the necessary `import` statement(s) in a `<Define>` element.

Comments can be included in `<Define>` code using normal Python conventions.

You can have multiple definitions in a single `<Define>` element; you can also use multiple `<Define>` elements.

The preprocessor executes *all* `<Define>` elements in the input file before it does anything else. Because of this:

* It isn't useful to redefine variables or functions; only the final definitions will be retained. An unfortunate consequence of this is that you can't have `<Define>`d variables or functions local to a sub-branch within your XML tree.
* It isn't possible to refer to values that are evaluated in [XML element `{expressions}`s](#expressions) (*eg*, `"{SELF.width}"`). Such values need to be passed to Python functions as parameters, as in the `centre()` example above.

#### WFF Data Source Values

[WFF data source values](https://developer.android.com/training/wearables/wff/common/attributes/source-type), which are equivalent to [Watch Face Studio tag values](https://developer.samsung.com/watch-face-studio/user-guide/tag-expression.html), aren't available until the watchface is running on a real watch or virtual device. Therefore, such values can't be used in `<Define>` elements because those are evaluated before the watchface is even built. However, there are a few ways to avoid repeating expressions involving data sources.

A string variable can contain the names of data sources; *eg*:

    myTagEquation = "[COMPLICATION.TITLE] != null &amp;&amp; [COMPLICATION.MONOCHROMATIC_IMAGE] == null"

This could then be used in an `{expression}` like this:

    <Expression name="symmetric">
        {myTagEquation}
    </Expression>

This can be useful if such blocks of code need to be repeated (in which case, consider putting them in a [`<Symbol>`](#symbol)).

You can write Python functions that take data source names as parameters and return a string representation of an equation; *eg*:

    MY_CONSTANT = 4
    def myFunc(tagString, y):
	    return '({tagString})*{y}'.format(tagString=tagString, y=y)

Such a function could be used in an `{expression}` like this:

    "{1 + MY_CONSTANT} + {myFunc('[SECOND] + 2', 3)}"

After preprocessing, the resulting string would be:

    "5 + ([SECOND] + 2)*3"

Note that embedding string literals (*eg*, `'[SECOND]'`) within attribute values may require cunning use of different types of quotation marks.

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

All `<Symbol>` elements must be direct children of the `<Watchface>` element.

`<Use>` elements can be placed wherever the contents of the corresponding `<Symbol>` would be valid.

The `<Symbol>` element itself is not written to the output `watchface.xml` file. Only copies of the *contents* of the `<Symbol>`, as specified by `<Use>` elements, are written.

A `<Symbol>` can contain more than one immediate child element. All such children (and their sub-elements) will be inserted when `<Use>`d.

A `<Symbol>` can contain one or more `<Use>` elements, which must refer to other `<Symbol>`s. In this way, `<Symbol>`s can be hierarchical.

A `<Symbol>` can't contain other `<Symbol>` elements (but see above). All `<Symbol>`s are considered to be global regardless of where they are declared; there is no way to limit a `<Symbol>`'s accessibility.

`<Symbol>`s can include [`{expressions}`s](#expressions) which can, in turn, include variables and functions defined in [`<Define>`](#defines) elements. The example above contains several of these (although the `<Define>` element is not shown).

`<Symbol>` and `<Use>` can reduce the size of, and duplication in, your source file, but they won't do so for your `watchface.xml` file (which is used on the watch). This is because the preprocessor applies `<Symbol>` and `<Use>` elements *before* the watchface build process happens. It has to be this way because WFF does not support `<Symbol>` and `<Use>`.

#### <a id="use_attrib"></a>Customising `<Use>` Instances with Top-level Attributes

`<Symbol>` and `<Use>` allow you to reuse similar elements without copying and pasting. However, you will often want to make minor adjustments to each instance; *eg*, specifying different `x` and `y` values. There are a few ways to achieve this.

If you specify attribute values in a `<Use>` element, those values (except for that of `href`) will be applied to *all* of the top-level elements in the `<Symbol>` when it is inserted. The example above uses this feature: the second `<Use>` element overrides the value of the `<Symbol>`'s `x` attribute, so the second circle will have a different x value to that of the first circle.

Attribute values specified in a `<Use>` element do not change the `<Symbol>`; they're only applied to the *copy* of the `<Symbol>` that's inserted in place of the `<Use>`. Subsequent `<Use>`s of the same `<Symbol>` will not include attribute values specified in prior `<Use>`s.

> **Warning:** [`{expression}`s](#expressions) in attribute values are processed in the order in which the attributes appear in their element. Therefore, make sure you declare attributes with dependent values _after_ those on which they depend. WFF doesn't care about the order on which attributes are declared. Setting a bogus default value in a `<Symbol>` is okay if the actual value will be supplied by a `<Use>` element. Adding attributes via `<Use>` after the element has been declared will put the new attributes _after_ the predeclared attributes, so the new attribute's values won't be accessible by attributes declared earlier. So, this won't work:

        <Symbol id="icon">
            <PartImage
                width="{SELF.height}"
                ...
            </PartImage>
        </Symbol>
        <Use href="icon" height="{MY_SIZE}" />

> ...because `height` will be added to the `<PartImage>`'s attributes _after_ `width`, so `SELF.height` isn't known when processing the `width` `{expression}`. However, this *will* work:

        <Symbol id="icon">
            <PartImage
                height="0"
                width="{SELF.height}"
                ...
            </PartImage>
        </Symbol>
        <Use href="icon" height="{MY_SIZE}" />

Attributes with names that start with `data-` (*eg*, `data-gauge-diameter`) will be deleted at the end of preprocessing. This can be useful for attributes that will be used internally by the `<Use>` instance (*eg*, `{PARENT.data-gauge-diameter}`) but which are not valid in WFF.

> **Warning:** if you employ `data-` attributes in expressions, bear in mind that minus signs can be confused with hyphens in attribute names; *eg*, `PARENT.data-gauge-diameter-10`. If you intend to subtract, put a space before the minus sign; *eg*, `PARENT.data-gauge-diameter - 10`.

> **Tip:** Within `<Symbol>` definitions, you can initialise attribute values (including those in sub-elements) to default values. This way, you don't need to specify them when the `<Symbol>` is `<Use>`d and the defaults are appropriate. You only need to specify attribute values in `<Use>` when the values specified within the `<Symbol>` need to be changed.

#### <a id="transform"></a>`<Transform>`

A more flexible way to customise `<Symbol>` attribute values is to include one or more `<Transform>` elements within the relevant `<Use>`; *eg*: if your `<Symbol>` is:

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

<a id="xpath"></a>The `href` attribute of the `<Transform>` element can accept any [`XPath`](https://docs.python.org/3/library/xml.etree.elementtree.html#xpath-support) expression supported by Python's [`eTree`](https://docs.python.org/3/library/xml.etree.elementtree.html#) implementation; _eg_:

* `"PartDraw"` matches all `<PartDraw>` elements that are direct children of the `<Symbol>`

* `"PartDraw/Arc"` matches all `<Arc>` elements that are direct children of `<PartDraw>` elements that are direct children of the `<Symbol>`

* `"PartDraw[2]"` matches the second `<PartDraw>` element that is direct child of the `<Symbol>`

* `".//Arc"` matches all `<Arc>` elements anywhere in the `<Symbol>`

* `".//*[@direction='CLOCKWISE']"` matches elements of any type that have an attribute named `direction` with a value of `CLOCKWISE`.

> **Warning:** `<Transform>` elements will be applied to *all* elements in the `<Symbol>` that match the `href` value, and not just the first match. Be sure that `href` selects only the element(s) that you want to change.

Attribute value changes specified in a `<Use> <Transform>` element don't change the `<Symbol>`; they're only applied to the *copy* of the `<Symbol>` that's inserted in place of the `<Use>`. Subsequent `<Use>`s of the same `<Symbol>` will not include attribute value changes specified in prior `<Use> <Transform>`s.

The preprocessor's `<Transform>` element is not the same as WFF's `<Transform>` element. The preprocessor's `<Transform>` element can only appear within a `<Use>` element, takes effect when the preprocessor is executed (as opposed to when the watchface is running), and requires a `href` attribute.

You can usually achieve the same effect as `<Transform>` by [setting attribute values directly in the `<Use>` element](#use_attrib), and copying them internally within the `<Symbol>` with [`PARENT`](#self_parent) or [`SELF`](#self_parent). This can be more concise if you need to set multiple attributes to the same (or related) value. Remember that attributes that aren't valid WFF for the top-level elements in the `<Symbol>` should have names that start with `data-` so they'll be deleted after preprocessing.

#### <a id="delete"></a>`<Delete>`

`<Delete>` is similar to `<Transform>`, except that it simply removes elements (including their children) from the `<Symbol>` that match its `href` attribute value. `href` can take [XPath expressions](#xpath).

> **Warning:** `<Delete>` elements will be applied to *all* elements in the `<Symbol>` that match their `href` values, and not just the first match. Be sure that `href` selects only the element(s) that you want to delete.

Elements that are deleted by a `<Use> <Delete>` element do not change the `<Symbol>`; they're only applied to the *copy* of the `<Symbol>` that's inserted in place of the `<Use>`. Subsequent `<Use>`s of the same `<Symbol>` will still contain elements that were deleted in prior `<Use> <Delete>`s.

Because you can delete elements from a `<Symbol>` when you `<Use>` it, but you can't add new elements, you should include all possibly-relevant elements in your `<Symbol>`s.

#### <a id="candidates"></a>`<Symbol>` Candidate Selection

Most IDEs and code editors can highlight differences between two documents. This can be a useful way of assessing whether two blocks of code have enough similarities to justify converting them to a `<Symbol>`, and it can show what `<Transform>`s and `<Delete>`s are necessary to adapt the `<Symbol>` to each `<Use>` instance. You may need to copy each code block into a separate document to facilitate comparison.

---

### <a id="expressions"></a>XML Element `{Expression}`s

In some places, text enclosed in curly brackets `{ }` will be executed as a Python expression, and the resulting value will replace the bracketted text.

#### Example

    <PartDraw
        x = "{100+200}"
        ...

#### Notes

`{expression}`s will be executed and replaced in the following contexts:

* XML attribute values (as in the example above)

* XML element text (*eg*, WFF [`<Template>`](https://developer.android.com/training/wearables/wff/group/part/text/formatter/template) elements)

* XML element tail (rarely/never used in WFF).

An attribute value string can contain normal text as well as an `{expression}`; *eg*:

    <Group name="complic{PARENT.slotId}" ...

An attribute value string can contain more than one `{expression}`; *eg*:

    "foo {expression1} bar {expression2} baz"

Everything between the opening and closing curly brackets must be a Python expression.

`{expression}`s can use variables and functions that have been declared in [`<Define>`](#defines) elements, as well as any standard Python functions. If you need to use functions that are defined in Python modules (*eg*, `math.sqrt()`), include the necessary `import` statement(s) in a [`<Define>`](#defines) element.

Mathematical expressions in `<Define>` or `{expression}` can result in non-integer values, but some WFF attributes (*eg*, x) require integers. Use Python's `round()` function in such expressions.

<a id="self_parent"></a>Two special variables can be used within `{expression}`s:

* `SELF` refers to the current element. This can be used to access attribute values that have been previously defined in the current element; *eg*, `width="{SELF.height * 2}"`.

* `PARENT` refers to the parent of the current element. If the required attribute hasn't been defined on the parent element, `PARENT` will consider the parent's parent, and so on up the XML tree. `PARENT` can be used in two ways:

  * `PARENT.attributeName` returns the parent's value of the named attribute.

  * `PARENT` without an attribute name returns the parent's value of the attribute that is currently being defined; *eg*, `width="{PARENT}"` will set the current element's width to the same value as that of its parent.

[WFF data source values](https://developer.android.com/training/wearables/wff/common/attributes/source-type), which are equivalent to [Watch Face Studio tag values](https://developer.samsung.com/watch-face-studio/user-guide/tag-expression.html), aren't available until the watchface is running on a real watch (or virtual device). Therefore, such values can't be used in preprocessor `{expression}`s because `{expression}`s are evaluated before the watchface is even built. However, it is possible to use data source *names* in `{expression}`s. For example, the XML code to display a `<PartImage>` for an `AMBIENT` (AOD) icon is almost identical to that for a non-AMBIENT icon. The only difference will often be that one `<PartImage>` will use a `[COMPLICATION.MONOCHROMATIC_IMAGE_AMBIENT]` whereas the other will use a `[COMPLICATION.MONOCHROMATIC_IMAGE]`. You can write a `<Symbol id="iconVariant">` to handle both cases. The code within the `<Symbol>` could specify `[COMPLICATION.MONOCHROMATIC_IMAGE]` so that `<Use href="iconVariant"/>` would display it. When the `AMBIENT` variant needs to be displayed instead, the `<Symbol>` could be `<Use>`d again but with the data source value changed; *eg*:

    <Use href="iconVariant">
        <Transform
            href=".//Image"
            target="resource"
            value="[COMPLICATION.MONOCHROMATIC_IMAGE_AMBIENT]" />
    </Use>

(In a full implementation, you would also need to transform `alpha` and `<Variant>` to ensure that only one image is displayed.)

---

### <a id="full_example"></a>Example

A complete example of a preprocessor input file is [here](example/watchface-pp.xml). The corresponding `watchface.xml` produced by the preprocessor is [here](example/watchface.xml).

> **Note:** In this artifical example, the input file is larger than the output file. This is not normally the case because extensive `<Use>` elements reduce duplication. Moreover, the input file can be easier to develop and maintain because it avoids duplication and allows meaningfully-named variables and functions.

## <a id="installation"></a>INSTALLATION

Install a relatively recent version of [Python](https://www.python.org/) (*eg*, 3.13+).

Put `preprocess.py` somewhere where you can conveniently access it from your watchface project. For example, if you use the same file structure as Google's [samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat), you could put `preprocess.py` in the same folder as `gradlew`.

> **IMPORTANT**: If your project already contains a `watchface\src\main\res\raw\watchface.xml` file (and it probably does), ***COPY THIS FILE TO SOMEWHERE SAFE*** because you will probably use the preprocessor to overwrite it.

## <a id="usage"></a>USAGE

### <a id="prepare"></a>Prepare Input File

Obtain, create or edit an XML file (suggested name: `watchface-pp.xml`) that contains WFF code and any preprocessor features that you want to use. You can save this anywhere; your project's `watchface` subfolder is recommended.

> **Tip:** For an initial test, you don't have to use any preprocessor features; you can copy a standard `watchface.xml` file.

> **Tip:** Some lazy ways to obtain an initial file are:
>  * [Google's samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat)
>  * `watchface.xml` extracted from a [Samsung Watch Face Studio (WFS)](https://developer.samsung.com/watch-face-studio/overview.html) project:
>    * 'Publish' the project in WFS.
>    * Find the resulting `.aab` file in `build\[project]`.
>    * Append `.zip` to the `.aab` file's name.
>    * Copy `base\res\raw\watchface.xml` from within the `.aab.zip` file.
>    * Restore the `.aab` file's name by removing the `.zip`.
>  * [Empty WFF boilerplate project](https://github.com/gondwanasoft/wff-boilerplate).

> **Tip:** To avoid confusion, name your preprocessor input file something other than `watchface.xml`; *eg*, `watchface-pp.xml`.

> **Tip:** [WFS](https://developer.samsung.com/watch-face-studio/overview.html) sometimes uses XML `CDATA` strings in `watchface.xml` files it creates. The XML parser used by the preprocessor converts `CDATA` strings into escaped XML; *eg*: `"<![CDATA[...&&...]]>"` becomes `"...&amp;&amp;..."`. The watchface build process is happy with this. You may find the need to use escaped XML characters in other situations, such as `&gt;` in place of `>` in element text.

### <a id="run"></a>Run the Preprocessor

From a command prompt, execute `preprocess.py`, passing the input filename and output filename as parameters; *eg*:

    preprocess.py watchface\watchface-pp.xml watchface\src\main\res\raw\watchface.xml

If there were no errors, the output file will have been created. If you like, you can look at it in a text/code editor to see the code generated by the preprocessor.

> <a id="ugly"></a>**Tip:** The formatting of the XML file generated by the preprocessor can be ugly. To make the file easier to understand, format/prettify/beautify it using an IDE, code editor or other app.

`preprocess.py` will normally refuse to write the output file if doing so would overwrite an extant file. To allow it to overwrite, add the `-y` command line parameter.

### <a id="build"></a>Build and Test Watchface

Use the output file (typically `watchface.xml`) to build and test the watchface as you normally would (*eg*, see [Google's instructions](https://developer.android.com/training/wearables/wff/setup) and [samples](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat)).

### <a id="debugging"></a>Debugging

If the preprocessor can't process the input file, it will either display an error message or throw an uncaught exception. In either case, the console output should help you to identify the problem.

> **Note:** Processing stops as soon as one error is encountered. There could be multiple errors in the input file, so you need to keep correcting errors and rerunning the preprocessor until it completes successfully.

If the error message doesn't help, examine the output file to see how it differs from what you wanted.

For additional information, you can run `preprocess.py` again but with the `-d` command line parameter added. This will display a log of the preprocessor's activities and intermediate results, which may help you to work out what it's doing.

Even if the preprocessor completes successfully, it's eminently possible for the output file to be rejected by the watchface build process (`gradle`), or for the resulting watchface to look wrong or behave unexpectedly. Examine the output file and/or use `-d` to work out why.

> <a id="validator"></a>**Tip:** If you get errors when you attempt to build the watchface, use the [Format validator](https://github.com/google/watchface/tree/main/third_party/wff) to check your `watchface.xml`. Ideally, you always do this before you attempt to build the watchface, since it can provide much more useful error messages than the build process. Be aware that line numbers (*etc*) reported by the validator refer to `watchface.xml` rather than the preprocessor's input file (*eg*, `watchface-pp.xml`).

> **Tip:** Many WFF elements can be given a `name` attribute. Using unique values for `name`s can help you to match elements between your `watchface-pp.xml` and `watchface.xml` files. This can be especially useful since comments in the input file are not included in the output file. Be aware that, if you employ `<Use>` more than once for a particular `<Symbol>`, elements within the `<Symbol>` will be repeated in `watchface.xml` so `name` attributes will no longer be unique.

#### <a id="pp_log"></a>`pp-log()`

The preprocessor provides a `pp_log()` function that can be called within `watchface-pp.xml` [`<Define>`](#defines) functions and attribute value [`{expression}`](#expressions)s. It prints the value and type of its first argument to the console when `preprocess.py` is executed. Use it like this:

    pp_log(expression[, prompt])

* `expression`: Python code for the value that you want to display.
* `prompt`: an optional prompt to print before the value of the expression.

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

> **Tip:** You may need to employ a variety of types of quotation marks when embedding a call to `pp_log()` in an attribute value string.

## <a id="limitations"></a>LIMITATIONS

The preprocessor uses two insecure Python functions ([`exec()`](https://docs.python.org/3/library/functions.html#exec) and [`eval()`](https://docs.python.org/3/library/functions.html#eval)). It makes no attempt to ameliorate the risks associated with these. You should only use the preprocessor on input files that you trust.

The preprocessor will catch and report some error conditions nicely. However, many error conditions will not be caught and will result in the preprocessor throwing Python exceptions.

The preprocessor doesn't check whether the file it creates is valid WFF XML (see [tip](#validator)).

Python code in `<Define>` elements is global, rather than being encapsulated within the scope in which it is declared.

`<Symbol>`s are global, rather than being encapsulated within the scopes in which they are declared.

[Indentation](#indentation) of Python code in `<Define>` elements is rudimentary. Using `Tab` characters is especially risky; stick to `space`s.

IDEs and code editors are unlikely to provide coding assistance for Python code in `<Define>` elements or `{expression}`s. This is because such code is considered to be XML element text or attribute value strings; only the preprocessor knows otherwise.

> **Tip:** If you're desperate for Python coding help, put the Python code in a `.py` file and open it in a Python development environment.

`watchface-pp.xml` or `watchface.xml` files used by the preprocessor can't be imported into [Samsung's Watch Face Studio](https://developer.samsung.com/watch-face-studio/overview.html) because that app doesn't support importing XML.

The formatting of the XML file generated by the preprocessor can be ugly (see [tip](#ugly)).

XML comments in the input file are not included in the output file.

## <a id="applications"></a>OTHER APPLICATIONS

Although `preprocessor.py` was written specifically to help with WFF XML, the approach is fairly general. As a result, it should work in many other situations in which XML file generation can benefit from its features. Possible issues include:

* XML element tags used by the preprocessor (`<Define>`, *etc*) may clash with the semantics of the XML schema being used.
* The use of curly brackets `{ }` to embed expressions may clash with other uses of such brackets.
* The output file will be reformatted.
* XML `<!--comments-->` will not appear in the output file.
* `CDATA` strings and escape characters (`&amp;`, *etc*) may be changed.