Document control page. Synthetic fixture, not a real specification.

# 1 Introduction {#_Toc100001}

This document describes the demo lamp function.

## 1.1 Scope {#_Toc100002}

Applies to the demo lamp ECU only.

# 2 Function Description {#_Toc100003}

## 2.1 Lamp Control {#_Toc100004}

The lamp shall turn on when the switch is ON. See [Lamp Timing](#_Ref200001).

### 2.1.1 Overview

Short overview.

### 2.1.2 Lamp Timing []{#_Ref200001 .anchor}

The lamp shall turn on within 100 ms.

| Parameter | Value | Unit |
|-----------|-------|------|
| T_on      | 100   | ms   |

![Timing chart](images/image1.png)

#### 2.1.2.1 Fault Handling <a id="_Ref200002"></a>

On fault, see [bus timeout](9999ZXXXXB000_E_(Demo%20Bus)_260101.docx#_Ref300001)
and [unknown spec](8888ZXXXXC000_E_(Other)_250101.docx#_Ref999999).

##### 2.1.2.1.1 Retry

Retry up to 3 times. Broken ref: [missing](#_Ref404404).

```
# not a heading, inside code
```

## 2.2 Overview

Second overview with a duplicate title. Missing image: ![x](images/missing.png)

# 3 References

External: [site](https://example.com).
