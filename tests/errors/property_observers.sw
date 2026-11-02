struct Counter {
    var value: Int = 0 {
        didSet {
            print("changed")
        }
    }
}
var counter = Counter()
counter.value = 1
